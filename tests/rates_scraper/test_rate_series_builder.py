from datetime import date

import pytest
from support.rates import BTC, EUR, rate

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource
from aml_etl.rates_scraper.date_range import DateRange
from aml_etl.rates_scraper.rate_series_builder import MissingRatesError, RateSeriesBuilder


def test_middle_gap_is_carried_forward_and_flagged():
    rng = DateRange(date(2022, 9, 1), date(2022, 9, 3))
    result = RateSeriesBuilder().complete(
        [rate(EUR, 1, 1.0), rate(EUR, 3, 1.2)], rng, [Currency.EUR]
    )
    sep2 = next(r for r in result if r.rate_date == date(2022, 9, 2))
    assert sep2.usd_per_unit == 1.0 and sep2.is_filled
    assert [r.is_filled for r in result] == [False, True, False]


def test_leading_gap_uses_rate_from_before_range():
    rng = DateRange(date(2022, 9, 1), date(2022, 9, 2))
    aug31 = ExchangeRate(Currency.BTC, date(2022, 8, 31), 20000.0, RateSource.COINMARKETCAP, "u")
    result = RateSeriesBuilder().complete([aug31], rng, [Currency.BTC])
    assert [(r.rate_date.day, r.usd_per_unit, r.is_filled) for r in result] == [
        (1, 20000.0, True),
        (2, 20000.0, True),
    ]
    assert all(r.source is RateSource.COINMARKETCAP and r.source_url == "u" for r in result)


def test_leading_gap_without_earlier_rate_uses_first_later_rate():
    rng = DateRange(date(2022, 9, 1), date(2022, 9, 2))
    result = RateSeriesBuilder().complete([rate(EUR, 2, 1.1)], rng, [Currency.EUR])
    assert [(r.usd_per_unit, r.is_filled) for r in result] == [(1.1, True), (1.1, False)]


def test_usd_is_fixed_one():
    rng = DateRange(date(2022, 9, 1), date(2022, 9, 2))
    result = RateSeriesBuilder().complete([], rng, [Currency.USD])
    assert {(r.usd_per_unit, r.source) for r in result} == {(1.0, RateSource.FIXED)}
    assert len(result) == 2


def test_currency_without_any_rate_raises():
    with pytest.raises(MissingRatesError, match="JPY"):
        RateSeriesBuilder().complete(
            [], DateRange(date(2022, 9, 1), date(2022, 9, 1)), [Currency.JPY]
        )


def test_real_rate_wins_over_previously_filled_rate_for_same_day():
    rng = DateRange(date(2022, 9, 1), date(2022, 9, 1))
    result = RateSeriesBuilder().complete(
        [rate(BTC, 1, 5.0, filled=True), rate(BTC, 1, 7.0)], rng, [Currency.BTC]
    )
    assert [(r.usd_per_unit, r.is_filled) for r in result] == [(7.0, False)]


def test_previously_filled_rate_stays_flagged():
    rng = DateRange(date(2022, 9, 1), date(2022, 9, 1))
    result = RateSeriesBuilder().complete([rate(BTC, 1, 5.0, filled=True)], rng, [Currency.BTC])
    assert [(r.usd_per_unit, r.is_filled) for r in result] == [(5.0, True)]
