from collections.abc import Iterable

import polars as pl

from aml_etl.common.exchange_rates import ExchangeRate

RATE_SCHEMA = {"currency": pl.Utf8, "rate_date": pl.Date, "usd_per_unit": pl.Float64}


class MissingExchangeRatesError(RuntimeError):
    pass


class RateTable:
    def __init__(self, rates: Iterable[ExchangeRate]) -> None:
        rows = [
            {
                "currency": rate.currency.value,
                "rate_date": rate.rate_date,
                "usd_per_unit": rate.usd_per_unit,
            }
            for rate in rates
        ]
        if not rows:
            raise MissingExchangeRatesError(
                "No exchange rates found in Atlas; run rates-scraper first"
            )
        self._frame = pl.DataFrame(rows, schema=RATE_SCHEMA).unique(
            subset=["currency", "rate_date"], keep="first"
        )

    def as_frame(self) -> pl.DataFrame:
        return self._frame
