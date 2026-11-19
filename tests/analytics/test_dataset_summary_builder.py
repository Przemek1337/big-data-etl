from datetime import UTC, datetime

import pytest
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.dataset_summary_builder import DatasetSummaryBuilder, NoTransactionsError
from aml_etl.common.dataset_variants import DatasetVariant


def build(transactions, mongo_database):
    builder = DatasetSummaryBuilder(transactions, mongo_database["data_quality"], lambda: NOW)
    return builder.build(DatasetVariant("HI-Small"))


@pytest.mark.integration
def test_summary_counts(seed, mongo_database):
    transactions = seed(
        [
            transaction_doc(is_laundering=True, amount_paid_usd=50.0),
            transaction_doc(timestamp=datetime(2022, 9, 5, 8, 0, tzinfo=UTC)),
            transaction_doc(payment_currency="EUR"),
            transaction_doc(dataset_variant="LI-Small", amount_paid_usd=999.0),
        ]
    )
    summary = build(transactions, mongo_database)
    assert (summary.transaction_count, summary.laundering_count) == (3, 1)
    assert summary.laundering_rate == pytest.approx(1 / 3) and summary.currency_count == 2
    assert summary.volume_usd == pytest.approx(250.0)
    assert summary.period_start == datetime(2022, 9, 1, 10, 0, tzinfo=UTC)
    assert summary.period_end == datetime(2022, 9, 5, 8, 0, tzinfo=UTC)
    assert (summary.rows_read, summary.duplicate_rows, summary.last_import_at) == (0, 0, None)
    assert summary.rejections == {} and summary.rows_rejected == 0


@pytest.mark.integration
def test_summary_includes_data_quality_report(seed, mongo_database):
    mongo_database["data_quality"].insert_one(
        {
            "_id": "HI-Small",
            "rows_read": 12,
            "rows_rejected": 2,
            "rejections": {"invalid_amount": 2},
            "exact_duplicate_rows": 3,
            "completed_at": NOW,
        }
    )
    summary = build(seed([transaction_doc()]), mongo_database)
    assert (summary.rows_read, summary.rows_rejected, summary.duplicate_rows) == (12, 2, 3)
    assert summary.rejections == {"invalid_amount": 2} and summary.last_import_at == NOW


@pytest.mark.integration
def test_summary_without_transactions_raises(seed, mongo_database):
    with pytest.raises(NoTransactionsError, match="transactions-etl"):
        build(seed([]), mongo_database)
