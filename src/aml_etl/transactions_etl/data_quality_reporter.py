from typing import Any

from pymongo.collection import Collection

from aml_etl.transactions_etl.import_progress import ImportProgress


class DataQualityReporter:
    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        self._collection = collection

    def publish(self, progress: ImportProgress) -> None:
        rejected = progress.rows_rejected
        document = {
            "_id": progress.variant,
            "rows_read": progress.rows_read,
            "rows_loaded": progress.rows_inserted + progress.rows_already_present,
            "rows_rejected": rejected,
            "rejections": dict(progress.rejections),
            "rejection_rate": rejected / progress.rows_read if progress.rows_read else 0.0,
            "exact_duplicate_rows": progress.duplicate_rows,
            "completed_at": progress.completed_at,
        }
        self._collection.replace_one({"_id": progress.variant}, document, upsert=True)
