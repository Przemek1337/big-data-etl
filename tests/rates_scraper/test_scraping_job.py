from pathlib import Path

import pytest
from support.csv_rows import write_csv

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.rates_scraper.coinmarketcap_page_parser import CoinMarketCapPageParser
from aml_etl.rates_scraper.date_range import TransactionDateRangeDetector
from aml_etl.rates_scraper.rate_series_builder import RateSeriesBuilder
from aml_etl.rates_scraper.scraping_job import ExchangeRateScrapingJob
from aml_etl.rates_scraper.x_rates_page_parser import XRatesPageParser

FIXTURES = Path(__file__).parent / "fixtures"


class FixtureFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch(self, url: str) -> str:
        self.urls.append(url)
        name = "x_rates_2022-09-01.html" if "x-rates" in url else "coinmarketcap_2022-09-01.html"
        return (FIXTURES / name).read_text(encoding="utf-8")


class FailingBitcoinFetcher(FixtureFetcher):
    def fetch(self, url: str) -> str:
        if "coinmarketcap" in url:
            raise RuntimeError("coinmarketcap down")
        return super().fetch(url)


def build_test_job(raw_dir, fetcher, database):
    return ExchangeRateScrapingJob(
        detector=TransactionDateRangeDetector(raw_dir),
        fetcher=fetcher,
        x_rates_parser=XRatesPageParser(),
        bitcoin_parser=CoinMarketCapPageParser(),
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
def test_fetches_one_page_per_day_from_each_source(tmp_path, mongo_database):
    write_csv(tmp_path / "HI-Small_Trans.csv", ["2022/09/01 00:20", "2022/09/03 10:00"])
    fetcher = FixtureFetcher()
    build_test_job(tmp_path, fetcher, mongo_database).run()
    assert [u for u in fetcher.urls if "coinmarketcap" in u] == [
        "https://coinmarketcap.com/historical/20220901/",
        "https://coinmarketcap.com/historical/20220902/",
        "https://coinmarketcap.com/historical/20220903/",
    ]
    assert len([u for u in fetcher.urls if "x-rates" in u]) == 3
    rates = mongo_database["exchange_rates"]
    assert rates.count_documents({}) == 3 * 15
    assert rates.count_documents({"is_filled": True}) == 0
    bitcoin = rates.find_one({"_id": "BTC:2022-09-02"})
    assert bitcoin["source"] == "coinmarketcap" and bitcoin["usd_per_unit"] == 20127.14


@pytest.mark.integration
def test_fiat_rates_survive_bitcoin_failure_and_are_not_refetched(tmp_path, mongo_database):
    write_csv(tmp_path / "HI-Small_Trans.csv", ["2022/09/01 00:20", "2022/09/02 00:20"])
    with pytest.raises(RuntimeError, match="coinmarketcap down"):
        build_test_job(tmp_path, FailingBitcoinFetcher(), mongo_database).run()
    fetcher = FixtureFetcher()
    build_test_job(tmp_path, fetcher, mongo_database).run()
    assert [u for u in fetcher.urls if "x-rates" in u] == []
    assert len([u for u in fetcher.urls if "coinmarketcap" in u]) == 2
    assert mongo_database["exchange_rates"].count_documents({}) == 2 * 15
