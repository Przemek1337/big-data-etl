from dataclasses import dataclass

import polars as pl

from aml_etl.transactions_etl.rate_table import RateTable

RATE_DATE_COLUMN = "rate_date"
PAID_RATE_COLUMN = "paid_usd_per_unit"
RECEIVED_RATE_COLUMN = "received_usd_per_unit"


@dataclass(frozen=True)
class EnrichmentResult:
    frame: pl.DataFrame
    missing_rate_count: int


class UsdEnricher:
    def __init__(self, rate_table: RateTable) -> None:
        self._rates = rate_table.as_frame()

    def transform(self, item: pl.DataFrame) -> EnrichmentResult:
        dated = item.with_columns(pl.col("timestamp").dt.date().alias(RATE_DATE_COLUMN))
        joined = self._with_rate(dated, "payment_currency", PAID_RATE_COLUMN)
        joined = self._with_rate(joined, "receiving_currency", RECEIVED_RATE_COLUMN)
        priced = joined.filter(
            pl.col(PAID_RATE_COLUMN).is_not_null() & pl.col(RECEIVED_RATE_COLUMN).is_not_null()
        )
        enriched = priced.with_columns(
            (pl.col("amount_paid") * pl.col(PAID_RATE_COLUMN)).alias("amount_paid_usd"),
            (pl.col("amount_received") * pl.col(RECEIVED_RATE_COLUMN)).alias("amount_received_usd"),
            (pl.col("payment_currency") != pl.col("receiving_currency")).alias("is_cross_currency"),
        ).drop(RATE_DATE_COLUMN, PAID_RATE_COLUMN, RECEIVED_RATE_COLUMN)
        return EnrichmentResult(enriched, item.height - enriched.height)

    def _with_rate(self, frame: pl.DataFrame, currency_column: str, alias: str) -> pl.DataFrame:
        rates = self._rates.rename({"currency": currency_column, "usd_per_unit": alias})
        return frame.join(
            rates, on=[currency_column, RATE_DATE_COLUMN], how="left", maintain_order="left"
        )
