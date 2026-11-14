from pathlib import Path

import pytest
from support.csv_rows import write_csv

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.rates_scraper.date_range import TransactionDateRangeDetector
from aml_etl.rates_scraper.rate_series_builder import RateSeriesBuilder
from aml_etl.rates_scraper.scraping_job import ExchangeRateScrapingJob
from aml_etl.rates_scraper.statmuse_bitcoin_page_parser import StatMuseBitcoinPageParser
from aml_etl.rates_scraper.x_rates_page_parser import XRatesPageParser

FIXTURES = Path(__file__).parent / "fixtures"


class FixtureFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch(self, url: str) -> str:
        self.urls.append(url)
        name = "x_rates_2022-09-01.html" if "x-rates" in url else "statmuse_bitcoin_2022-09.html"
        return (FIXTURES / name).read_text(encoding="utf-8")


def build_test_job(raw_dir, fetcher, database):
    return ExchangeRateScrapingJob(
        detector=TransactionDateRangeDetector(raw_dir),
        fetcher=fetcher,
        x_rates_parser=XRatesPageParser(),
        bitcoin_parser=StatMuseBitcoinPageParser(),
        series_builder=RateSeriesBuilder(),
        repository=ExchangeRateRepository(database),
        variants=[DatasetVariant("HI-Small")],
    )


@pytest.mark.integration
def test_second_run_fetches_no_pages(tmp_path, mongo_database):
    write_csv(tmp_path / "HI-Small_Trans.csv", ["2022/09/01 00:20"])
    fetcher = FixtureFetcher()
    job = build_test_job(tmp_path, fetcher, mongo_database)
    job.run()
    first_count = mongo_database["exchange_rates"].count_documents({})
    assert len(fetcher.urls) == 2
    fetcher.urls.clear()
    job.run()
    assert fetcher.urls == []
    assert mongo_database["exchange_rates"].count_documents({}) == first_count == 15


@pytest.mark.integration
def test_fetches_one_x_rates_page_per_day_and_bitcoin_in_windows(tmp_path, mongo_database):
    write_csv(tmp_path / "HI-Small_Trans.csv", ["2022/09/16 00:20", "2022/09/30 10:00"])
    fetcher = FixtureFetcher()
    build_test_job(tmp_path, fetcher, mongo_database).run()
    assert len([u for u in fetcher.urls if "x-rates" in u]) == 15
    assert [u.rsplit("/", 1)[1] for u in fetcher.urls if "statmuse" in u] == [
        "bitcoin-price-from-september-1-2022-to-september-15-2022",
        "bitcoin-price-from-september-16-2022-to-september-30-2022",
    ]
    assert mongo_database["exchange_rates"].count_documents({}) == 15 * 15
    assert (
        mongo_database["exchange_rates"].count_documents(
            {"_id": {"$regex": "^BTC"}, "is_filled": True}
        )
        == 0
    )


class FailingBitcoinFetcher(FixtureFetcher):
    def fetch(self, url: str) -> str:
        if "statmuse" in url:
            raise RuntimeError("statmuse down")
        return super().fetch(url)


@pytest.mark.integration
def test_fiat_rates_survive_bitcoin_failure_and_are_not_refetched(tmp_path, mongo_database):
    write_csv(tmp_path / "HI-Small_Trans.csv", ["2022/09/01 00:20", "2022/09/02 00:20"])
    with pytest.raises(RuntimeError, match="statmuse down"):
        build_test_job(tmp_path, FailingBitcoinFetcher(), mongo_database).run()
    fetcher = FixtureFetcher()
    build_test_job(tmp_path, fetcher, mongo_database).run()
    assert [u for u in fetcher.urls if "x-rates" in u] == []
    assert mongo_database["exchange_rates"].count_documents({}) == 2 * 15
