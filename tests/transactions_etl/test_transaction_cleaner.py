from collections import Counter
from datetime import UTC, datetime

import polars as pl
import pytest
from support.raw_frames import raw_frame, raw_row

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.transactions_etl.transaction_cleaner import RejectionReason, TransactionCleaner


def clean(*rows):
    return TransactionCleaner(DatasetVariant("HI-Small")).transform(raw_frame(*rows))


def test_valid_row_is_normalized():
    result = clean(raw_row(receiving_currency=" Brazil Real ", is_laundering="1"))
    record = result.frame.to_dicts()[0]
    assert record["_id"] == "HI-Small:0" and record["row_number"] == 0
    assert record["timestamp"] == datetime(2022, 9, 1, 0, 20, tzinfo=UTC)
    assert record["receiving_currency"] == "BRL" and record["payment_currency"] == "USD"
    assert record["is_laundering"] is True and record["from_bank"] == "010"
    assert record["amount_paid"] == pytest.approx(3697.34)
    assert record["dataset_variant"] == "HI-Small" and not result.rejections


def test_output_schema():
    assert clean(raw_row()).frame.schema == {
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


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"from_account": ""}, RejectionReason.MISSING_FIELD),
        ({"to_bank": "   "}, RejectionReason.MISSING_FIELD),
        ({"timestamp": "2022/13/01 00:00"}, RejectionReason.INVALID_TIMESTAMP),
        ({"amount_paid": "abc"}, RejectionReason.INVALID_AMOUNT),
        ({"amount_received": "inf"}, RejectionReason.INVALID_AMOUNT),
        ({"amount_paid": "NaN"}, RejectionReason.INVALID_AMOUNT),
        ({"amount_paid": "0"}, RejectionReason.NON_POSITIVE_AMOUNT),
        ({"amount_received": "-5"}, RejectionReason.NON_POSITIVE_AMOUNT),
        ({"payment_currency": "Zloty"}, RejectionReason.UNKNOWN_CURRENCY),
        ({"payment_format": "Barter"}, RejectionReason.UNKNOWN_PAYMENT_FORMAT),
        ({"is_laundering": "2"}, RejectionReason.INVALID_LABEL),
    ],
)
def test_invalid_rows_are_rejected_with_reason(overrides, reason):
    result = clean(raw_row(**overrides))
    assert result.frame.height == 0 and result.rejections == Counter({reason: 1})


def test_null_field_is_missing_field():
    frame = raw_frame(raw_row()).with_columns(pl.lit(None, dtype=pl.Utf8).alias("to_account"))
    result = TransactionCleaner(DatasetVariant("HI-Small")).transform(frame)
    assert result.rejections == Counter({RejectionReason.MISSING_FIELD: 1})


def test_row_with_two_defects_is_counted_once_by_priority():
    result = clean(raw_row(timestamp="bad", payment_currency="Zloty"))
    assert result.rejections == Counter({RejectionReason.INVALID_TIMESTAMP: 1})


def test_bad_row_does_not_shift_ids_of_good_rows():
    result = clean(raw_row(), raw_row(amount_paid="abc"), raw_row())
    assert result.frame["_id"].to_list() == ["HI-Small:0", "HI-Small:2"]


def test_exact_duplicates_are_kept_and_counted():
    result = clean(raw_row(), raw_row(), raw_row(), raw_row(amount_paid="5"))
    assert result.frame.height == 4 and result.duplicate_row_count == 2
    assert result.frame["_id"].n_unique() == 4 and not result.rejections


def test_empty_batch_is_handled():
    result = clean()
    assert result.frame.height == 0 and not result.rejections and result.duplicate_row_count == 0
