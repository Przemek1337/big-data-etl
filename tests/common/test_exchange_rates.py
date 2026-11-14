from datetime import date

import pytest
from support.rates import BTC, EUR, rate

from aml_etl.common.exchange_rates import ExchangeRateRepository, RateSource


@pytest.mark.integration
def test_upsert_is_idempotent(mongo_database):
    repository = ExchangeRateRepository(mongo_database)
    rates = [rate(EUR, 1, 1.0), rate(EUR, 2, 1.1)]
    repository.upsert_many(rates)
    repository.upsert_many(rates)
    assert mongo_database["exchange_rates"].count_documents({}) == 2
    assert repository.scraped_dates(RateSource.X_RATES) == {date(2022, 9, 1), date(2022, 9, 2)}


@pytest.mark.integration
def test_round_trip_and_filled_rates(mongo_database):
    repository = ExchangeRateRepository(mongo_database)
    rates = [rate(EUR, 1, 1.0), rate(BTC, 1, 20000.0), rate(BTC, 2, 20000.0, filled=True)]
    assert repository.upsert_many(rates) == 3
    assert sorted(repository.find_all(), key=lambda r: (r.currency, r.rate_date)) == sorted(
        rates, key=lambda r: (r.currency, r.rate_date)
    )
    assert repository.scraped_dates(RateSource.STATMUSE) == {date(2022, 9, 1)}
    assert repository.dates_with_rates(BTC) == {date(2022, 9, 1), date(2022, 9, 2)}
    stored = mongo_database["exchange_rates"].find_one({"_id": "BTC:2022-09-02"})
    assert stored["rate_date"].tzinfo is not None and stored["scraped_at"] is not None


@pytest.mark.integration
def test_upsert_of_nothing_is_a_no_op(mongo_database):
    assert ExchangeRateRepository(mongo_database).upsert_many([]) == 0
