import dataclasses
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pymongo.collection import Collection

from aml_etl.transactions_etl.csv_batch_reader import CsvBatch
from aml_etl.transactions_etl.transaction_cleaner import CleaningResult, RejectionReason
from aml_etl.transactions_etl.transaction_loader import LoadResult
from aml_etl.transactions_etl.usd_enricher import EnrichmentResult


class ImportStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True)
class ImportProgress:
    variant: str
    source_file_size: int
    next_row_number: int
    rows_read: int
    rows_inserted: int
    rows_already_present: int
    duplicate_rows: int
    rejections: dict[str, int]
    status: ImportStatus
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def start(cls, variant: str, source_file_size: int, now: datetime) -> Self:
        return cls(
            variant=variant,
            source_file_size=source_file_size,
            next_row_number=0,
            rows_read=0,
            rows_inserted=0,
            rows_already_present=0,
            duplicate_rows=0,
            rejections={},
            status=ImportStatus.IN_PROGRESS,
            started_at=now,
            updated_at=now,
            completed_at=None,
        )

    def after_batch(
        self,
        batch: CsvBatch,
        cleaning: CleaningResult,
        enrichment: EnrichmentResult,
        load: LoadResult,
        now: datetime,
    ) -> Self:
        rejections = Counter(self.rejections)
        for reason, count in cleaning.rejections.items():
            rejections[reason.value] += count
        if batch.malformed_line_count:
            rejections[RejectionReason.MALFORMED_LINE.value] += batch.malformed_line_count
        if enrichment.missing_rate_count:
            rejections[RejectionReason.MISSING_EXCHANGE_RATE.value] += enrichment.missing_rate_count
        return dataclasses.replace(
            self,
            next_row_number=batch.next_row_number,
            rows_read=self.rows_read + batch.frame.height + batch.malformed_line_count,
            rows_inserted=self.rows_inserted + load.inserted,
            rows_already_present=self.rows_already_present + load.already_present,
            duplicate_rows=self.duplicate_rows + cleaning.duplicate_row_count,
            rejections=dict(rejections),
            updated_at=now,
        )

    def completed(self, now: datetime) -> Self:
        return dataclasses.replace(
            self, status=ImportStatus.COMPLETED, updated_at=now, completed_at=now
        )

    @property
    def rows_rejected(self) -> int:
        return sum(self.rejections.values())


class ImportProgressTracker:
    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        self._collection = collection

    def load(self, variant: str) -> ImportProgress | None:
        document = self._collection.find_one({"_id": variant})
        if document is None:
            return None
        fields = {field.name: document[field.name] for field in dataclasses.fields(ImportProgress)}
        fields["status"] = ImportStatus(fields["status"])
        return ImportProgress(**fields)

    def save(self, progress: ImportProgress) -> None:
        document = dataclasses.asdict(progress)
        document["status"] = progress.status.value
        document["_id"] = progress.variant
        self._collection.replace_one({"_id": progress.variant}, document, upsert=True)
