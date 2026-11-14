from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from aml_etl.common.currencies import Currency
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.payment_formats import PaymentFormat
from aml_etl.transactions_etl.transaction_ids import ID_COLUMN, add_transaction_ids
from aml_etl.transactions_etl.transaction_schema import RAW_COLUMNS, ROW_NUMBER_COLUMN

TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M"
REASON_COLUMN = "rejection_reason"
PARSED_PREFIX = "parsed_"
CURRENCY_CODES = {currency.dataset_name: currency.value for currency in Currency}
PAYMENT_FORMATS = [payment_format.value for payment_format in PaymentFormat]
LABELS = ["0", "1"]
OUTPUT_COLUMNS = (
    ID_COLUMN,
    ROW_NUMBER_COLUMN,
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_received",
    "amount_paid",
    "receiving_currency",
    "payment_currency",
    "payment_format",
    "is_laundering",
    "dataset_variant",
)


class RejectionReason(StrEnum):
    MISSING_FIELD = "missing_field"
    INVALID_TIMESTAMP = "invalid_timestamp"
    INVALID_AMOUNT = "invalid_amount"
    NON_POSITIVE_AMOUNT = "non_positive_amount"
    UNKNOWN_CURRENCY = "unknown_currency"
    UNKNOWN_PAYMENT_FORMAT = "unknown_payment_format"
    INVALID_LABEL = "invalid_label"
    MALFORMED_LINE = "malformed_line"
    MISSING_EXCHANGE_RATE = "missing_exchange_rate"


@dataclass(frozen=True)
class CleaningResult:
    frame: pl.DataFrame
    rejections: Counter[RejectionReason]
    duplicate_row_count: int


def _parsed(column: str) -> pl.Expr:
    return pl.col(f"{PARSED_PREFIX}{column}")


class TransactionCleaner:
    def __init__(self, variant: DatasetVariant) -> None:
        self._variant = variant

    def transform(self, item: pl.DataFrame) -> CleaningResult:
        judged = self._judge(self._parse(self._trim(item)))
        valid = judged.filter(pl.col(REASON_COLUMN).is_null())
        duplicates = valid.height - valid.select(RAW_COLUMNS).n_unique()
        return CleaningResult(
            frame=self._normalize(valid),
            rejections=self._count_rejections(judged),
            duplicate_row_count=duplicates,
        )

    def _trim(self, frame: pl.DataFrame) -> pl.DataFrame:
        return frame.with_columns(pl.col(column).str.strip_chars() for column in RAW_COLUMNS)

    def _parse(self, frame: pl.DataFrame) -> pl.DataFrame:
        return frame.with_columns(
            pl.col("timestamp")
            .str.to_datetime(TIMESTAMP_FORMAT, strict=False, time_zone="UTC", time_unit="us")
            .alias(f"{PARSED_PREFIX}timestamp"),
            *(
                pl.col(column).cast(pl.Float64, strict=False).alias(f"{PARSED_PREFIX}{column}")
                for column in ("amount_received", "amount_paid")
            ),
            *(
                pl.col(column)
                .replace_strict(CURRENCY_CODES, default=None, return_dtype=pl.Utf8)
                .alias(f"{PARSED_PREFIX}{column}")
                for column in ("receiving_currency", "payment_currency")
            ),
        )

    def _judge(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = pl.any_horizontal(
            pl.col(column).is_null() | (pl.col(column) == "") for column in RAW_COLUMNS
        )
        amounts = (_parsed("amount_received"), _parsed("amount_paid"))
        invalid_amount = pl.any_horizontal(
            amount.is_null() | ~amount.is_finite() for amount in amounts
        )
        non_positive = pl.any_horizontal(amount <= 0 for amount in amounts)
        unknown_currency = (
            _parsed("receiving_currency").is_null() | _parsed("payment_currency").is_null()
        )
        reason = (
            pl.when(missing)
            .then(pl.lit(RejectionReason.MISSING_FIELD.value))
            .when(_parsed("timestamp").is_null())
            .then(pl.lit(RejectionReason.INVALID_TIMESTAMP.value))
            .when(invalid_amount)
            .then(pl.lit(RejectionReason.INVALID_AMOUNT.value))
            .when(non_positive)
            .then(pl.lit(RejectionReason.NON_POSITIVE_AMOUNT.value))
            .when(unknown_currency)
            .then(pl.lit(RejectionReason.UNKNOWN_CURRENCY.value))
            .when(~pl.col("payment_format").is_in(PAYMENT_FORMATS))
            .then(pl.lit(RejectionReason.UNKNOWN_PAYMENT_FORMAT.value))
            .when(~pl.col("is_laundering").is_in(LABELS))
            .then(pl.lit(RejectionReason.INVALID_LABEL.value))
            .otherwise(pl.lit(None, dtype=pl.Utf8))
        )
        return frame.with_columns(reason.alias(REASON_COLUMN))

    def _count_rejections(self, judged: pl.DataFrame) -> Counter[RejectionReason]:
        counts = (
            judged.filter(pl.col(REASON_COLUMN).is_not_null())
            .group_by(REASON_COLUMN)
            .len()
            .iter_rows()
        )
        return Counter({RejectionReason(reason): count for reason, count in counts})

    def _normalize(self, valid: pl.DataFrame) -> pl.DataFrame:
        normalized = valid.with_columns(
            _parsed("timestamp").alias("timestamp"),
            _parsed("amount_received").alias("amount_received"),
            _parsed("amount_paid").alias("amount_paid"),
            _parsed("receiving_currency").alias("receiving_currency"),
            _parsed("payment_currency").alias("payment_currency"),
            (pl.col("is_laundering") == "1").alias("is_laundering"),
            pl.lit(self._variant.name).alias("dataset_variant"),
        )
        return add_transaction_ids(normalized, self._variant).select(OUTPUT_COLUMNS)
