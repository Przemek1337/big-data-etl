import logging
from collections.abc import Sequence
from typing import Protocol

from aml_etl.common.currencies import Currency
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRate, ExchangeRateRepository, RateSource
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.settings import AmlSettings
from aml_etl.rates_scraper.date_range import DateRange, TransactionDateRangeDetector
from aml_etl.rates_scraper.http_page_fetcher import HttpPageFetcher, build_http_client
from aml_etl.rates_scraper.rate_series_builder import RateSeriesBuilder
from aml_etl.rates_scraper.statmuse_bitcoin_page_parser import (
    STATMUSE_WINDOW_DAYS,
    StatMuseBitcoinPageParser,
    statmuse_bitcoin_range_url,
)
from aml_etl.rates_scraper.x_rates_page_parser import XRatesPageParser, x_rates_url

logger = logging.getLogger(__name__)

BITCOIN_LOOKBACK_DAYS = 7


class PageFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class ExchangeRateScrapingJob:
    def __init__(
        self,
        detector: TransactionDateRangeDetector,
        fetcher: PageFetcher,
        x_rates_parser: XRatesPageParser,
        bitcoin_parser: StatMuseBitcoinPageParser,
        series_builder: RateSeriesBuilder,
        repository: ExchangeRateRepository,
        variants: Sequence[DatasetVariant],
    ) -> None:
        self._detector = detector
        self._fetcher = fetcher
        self._x_rates_parser = x_rates_parser
        self._bitcoin_parser = bitcoin_parser
        self._series_builder = series_builder
        self._repository = repository
        self._variants = variants

    def run(self) -> None:
        date_range = self._detector.detect(self._variants)
        logger.info("Transactions span %s to %s", date_range.start, date_range.end)
        self._repository.upsert_many(self._scrape_fiat(date_range))
        known = self._repository.find_all() + self._scrape_bitcoin(date_range)
        series = self._series_builder.complete(known, date_range, list(Currency))
        saved = self._repository.upsert_many(series)
        filled = sum(1 for rate in series if rate.is_filled)
        logger.info("Saved %d exchange rates (%d gap-filled)", saved, filled)

    def _scrape_fiat(self, date_range: DateRange) -> list[ExchangeRate]:
        already_scraped = self._repository.scraped_dates(RateSource.X_RATES)
        missing_days = [day for day in date_range.days() if day not in already_scraped]
        rates: list[ExchangeRate] = []
        for day in missing_days:
            url = x_rates_url(day)
            rates.extend(self._x_rates_parser.parse(self._fetcher.fetch(url), day, url))
        logger.info("Fetched %d x-rates pages", len(missing_days))
        return rates

    def _scrape_bitcoin(self, date_range: DateRange) -> list[ExchangeRate]:
        covered = self._repository.dates_with_rates(Currency.BTC)
        if all(day in covered for day in date_range.days()):
            logger.info("Fetched 0 Bitcoin pages")
            return []
        windows = self._full_windows(date_range.extended_backwards(BITCOIN_LOOKBACK_DAYS))
        rates: list[ExchangeRate] = []
        for window in windows:
            url = statmuse_bitcoin_range_url(window.start, window.end)
            rates.extend(self._bitcoin_parser.parse(self._fetcher.fetch(url), url))
        logger.info("Fetched %d Bitcoin pages", len(windows))
        return rates

    def _full_windows(self, date_range: DateRange) -> list[DateRange]:
        padding = -len(date_range.days()) % STATMUSE_WINDOW_DAYS
        return date_range.extended_backwards(padding).windows(STATMUSE_WINDOW_DAYS)


def build_scraping_job(settings: AmlSettings) -> ExchangeRateScrapingJob:
    return ExchangeRateScrapingJob(
        detector=TransactionDateRangeDetector(settings.raw_dir),
        fetcher=HttpPageFetcher(build_http_client()),
        x_rates_parser=XRatesPageParser(),
        bitcoin_parser=StatMuseBitcoinPageParser(),
        series_builder=RateSeriesBuilder(),
        repository=ExchangeRateRepository(MongoDatabaseFactory(settings).atlas()),
        variants=settings.dataset_variants,
    )
