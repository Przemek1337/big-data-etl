from datetime import UTC, date, datetime

import polars as pl
import pytest
from support.clean_frames import CLEAN_SCHEMA, clean_frame, eur, row, usd

from aml_etl.transactions_etl.rate_table import MissingExchangeRatesError, RateTable
from aml_etl.transactions_etl.usd_enricher import UsdEnricher


def test_empty_rate_table_points_to_scraper():
    with pytest.raises(MissingExchangeRatesError, match="rates-scraper"):
        RateTable([])


def test_rate_table_frame_schema():
    frame = RateTable([eur(date(2022, 9, 1), 1.0039)]).as_frame()
    assert frame.schema == {"currency": pl.Utf8, "rate_date": pl.Date, "usd_per_unit": pl.Float64}
    assert frame.to_dicts() == [
        {"currency": "EUR", "rate_date": date(2022, 9, 1), "usd_per_unit": 1.0039}
    ]


def test_converts_amounts_with_rate_of_transaction_day():
    table = RateTable(
        [eur(date(2022, 9, 1), 1.0039), eur(date(2022, 9, 2), 2.0), usd(date(2022, 9, 1))]
    )
    result = UsdEnricher(table).transform(
        clean_frame(
            row(
                amount_paid=100.0,
                payment_currency="EUR",
                amount_received=100.39,
                receiving_currency="USD",
                timestamp=datetime(2022, 9, 1, 23, 59, tzinfo=UTC),
            )
        )
    )
    record = result.frame.to_dicts()[0]
    assert record["amount_paid_usd"] == pytest.approx(100.39)
    assert record["amount_received_usd"] == pytest.approx(100.39)
    assert record["is_cross_currency"] is True and "rate_date" not in record
    assert result.missing_rate_count == 0


def test_same_currency_is_not_cross_currency_and_columns_are_appended():
    result = UsdEnricher(RateTable([usd(date(2022, 9, 1))])).transform(clean_frame(row()))
    assert result.frame.columns == [
        *CLEAN_SCHEMA,
        "amount_paid_usd",
        "amount_received_usd",
        "is_cross_currency",
    ]
    assert result.frame["is_cross_currency"].to_list() == [False]


def test_row_without_rate_is_dropped_and_counted():
    table = RateTable([usd(date(2022, 9, 1))])
    result = UsdEnricher(table).transform(clean_frame(row(payment_currency="JPY"), row()))
    assert result.frame["_id"].to_list() == ["HI-Small:1"] and result.missing_rate_count == 1
