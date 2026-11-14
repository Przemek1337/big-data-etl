from datetime import UTC, date, datetime
from typing import Any

import polars as pl

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource

CLEAN_SCHEMA = {
    "_id": pl.Utf8,
    "row_number": pl.Int64,
    "timestamp": pl.Datetime("us", "UTC"),
    "from_bank": pl.Utf8,
    "from_account": pl.Utf8,
    "to_bank": pl.Utf8,
    "to_account": pl.Utf8,
    "amount_received": pl.Float64,
    "amount_paid": pl.Float64,
    "receiving_currency": pl.Utf8,
    "payment_currency": pl.Utf8,
    "payment_format": pl.Utf8,
    "is_laundering": pl.Boolean,
    "dataset_variant": pl.Utf8,
}


def row(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "_id": "HI-Small:0",
        "row_number": 0,
        "timestamp": datetime(2022, 9, 1, 0, 20, tzinfo=UTC),
        "from_bank": "010",
        "from_account": "8000EBD30",
        "to_bank": "010",
        "to_account": "8000EBD30",
        "amount_received": 3697.34,
        "amount_paid": 3697.34,
        "receiving_currency": "USD",
        "payment_currency": "USD",
        "payment_format": "Reinvestment",
        "is_laundering": False,
        "dataset_variant": "HI-Small",
    }
    values.update(overrides)
    return values


def clean_frame(*rows: dict[str, Any]) -> pl.DataFrame:
    numbered = [
        {**item, "row_number": index, "_id": f"HI-Small:{index}"} for index, item in enumerate(rows)
    ]
    return pl.DataFrame(numbered, schema=CLEAN_SCHEMA)


def eur(day: date, value: float) -> ExchangeRate:
    return ExchangeRate(Currency.EUR, day, value, RateSource.X_RATES, "u")


def usd(day: date) -> ExchangeRate:
    return ExchangeRate(Currency.USD, day, 1.0, RateSource.FIXED, "")
