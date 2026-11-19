from collections import Counter
from datetime import UTC, datetime

import pytest
from support.clean_frames import clean_frame, row
from support.raw_frames import raw_frame, raw_row

from aml_etl.transactions_etl.csv_batch_reader import CsvBatch
from aml_etl.transactions_etl.import_progress import (
    ImportProgress,
    ImportProgressTracker,
    ImportStatus,
)
from aml_etl.transactions_etl.transaction_cleaner import CleaningResult, RejectionReason
from aml_etl.transactions_etl.transaction_loader import LoadResult
from aml_etl.transactions_etl.usd_enricher import EnrichmentResult

T0 = datetime(2022, 9, 20, 12, 0, tzinfo=UTC)
T1 = datetime(2022, 9, 20, 12, 5, tzinfo=UTC)
T2 = datetime(2022, 9, 20, 12, 9, tzinfo=UTC)


def batch(first, good_rows, malformed):
    frame = raw_frame(*[raw_row() for _ in range(good_rows)])
    return CsvBatch(first, first + good_rows + malformed, frame, malformed)


def test_progress_accumulates_counts():
    progress = ImportProgress.start("HI-Small", 100, T0)
    assert (progress.next_row_number, progress.status) == (0, ImportStatus.IN_PROGRESS)
    progress = progress.after_batch(
        batch(0, good_rows=4, malformed=1),
        CleaningResult(
            clean_frame(row(), row(), row()), Counter({RejectionReason.INVALID_AMOUNT: 1}), 1
        ),
        EnrichmentResult(clean_frame(row(), row()), 1),
        LoadResult(inserted=2, already_present=0),
        T1,
    )
    progress = progress.after_batch(
        batch(5, good_rows=2, malformed=0),
        CleaningResult(clean_frame(row()), Counter({RejectionReason.INVALID_AMOUNT: 1}), 0),
        EnrichmentResult(clean_frame(row()), 0),
        LoadResult(inserted=0, already_present=1),
        T2,
    )
    assert progress.next_row_number == 7 and progress.rows_read == 7
    assert (progress.rows_inserted, progress.rows_already_present) == (2, 1)
    assert progress.duplicate_rows == 1
    assert progress.rejections == {
        "invalid_amount": 2,
        "malformed_line": 1,
        "missing_exchange_rate": 1,
    }
    assert (progress.started_at, progress.updated_at, progress.completed_at) == (T0, T2, None)
    done = progress.completed(T2)
    assert done.status is ImportStatus.COMPLETED and done.completed_at == T2


@pytest.mark.integration
def test_tracker_round_trips_progress(mongo_database):
    tracker = ImportProgressTracker(mongo_database["import_runs"])
    assert tracker.load("HI-Small") is None
    progress = ImportProgress.start("HI-Small", 100, T0)
    tracker.save(progress)
    tracker.save(progress.completed(T1))
    assert tracker.load("HI-Small") == progress.completed(T1)
    assert mongo_database["import_runs"].count_documents({}) == 1
