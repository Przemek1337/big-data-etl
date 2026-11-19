import logging
from collections.abc import Sequence
from typing import Protocol

from aml_etl.common.currencies import Currency
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRate, ExchangeRateRepository, RateSource
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.settings import AmlSettings
from aml_etl.rates_scraper.coinmarketcap_page_parser import (
    CoinMarketCapPageParser,
    coinmarketcap_url,
)
from aml_etl.rates_scraper.date_range import DateRange, TransactionDateRangeDetector
from aml_etl.rates_scraper.http_page_fetcher import HttpPageFetcher, build_http_client
from aml_etl.rates_scraper.rate_series_builder import RateSeriesBuilder
from aml_etl.rates_scraper.x_rates_page_parser import XRatesPageParser, x_rates_url

logger = logging.getLogger(__name__)


class PageFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class ExchangeRateScrapingJob:
    def __init__(
        self,
        detector: TransactionDateRangeDetector,
        fetcher: PageFetcher,
        x_rates_parser: XRatesPageParser,
        bitcoin_parser: CoinMarketCapPageParser,
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
        self._repository.upsert_many(self._scrape_bitcoin(date_range))
        series = self._series_builder.complete(
            self._repository.find_all(), date_range, list(Currency)
        )
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
        already_scraped = self._repository.scraped_dates(RateSource.COINMARKETCAP)
        missing_days = [day for day in date_range.days() if day not in already_scraped]
        rates: list[ExchangeRate] = []
        for day in missing_days:
            url = coinmarketcap_url(day)
            rates.extend(self._bitcoin_parser.parse(self._fetcher.fetch(url), day, url))
        logger.info("Fetched %d CoinMarketCap pages", len(missing_days))
        return rates


def build_scraping_job(settings: AmlSettings) -> ExchangeRateScrapingJob:
    return ExchangeRateScrapingJob(
        detector=TransactionDateRangeDetector(settings.raw_dir),
        fetcher=HttpPageFetcher(build_http_client()),
        x_rates_parser=XRatesPageParser(),
        bitcoin_parser=CoinMarketCapPageParser(),
        series_builder=RateSeriesBuilder(),
        repository=ExchangeRateRepository(MongoDatabaseFactory(settings).atlas()),
        variants=settings.dataset_variants,
    )
