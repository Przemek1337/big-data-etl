from dataclasses import dataclass
from typing import Any

import polars as pl
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

DUPLICATE_KEY_CODE = 11000


@dataclass(frozen=True)
class LoadResult:
    inserted: int
    already_present: int


class TransactionLoader:
    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        self._collection = collection

    def load(self, item: pl.DataFrame) -> LoadResult:
        if item.height == 0:
            return LoadResult(0, 0)
        try:
            self._collection.insert_many(item.to_dicts(), ordered=False)
        except BulkWriteError as error:
            write_errors = error.details.get("writeErrors", [])
            if any(entry.get("code") != DUPLICATE_KEY_CODE for entry in write_errors):
                raise
            if error.details.get("writeConcernErrors"):
                raise
            return LoadResult(int(error.details.get("nInserted", 0)), len(write_errors))
        return LoadResult(item.height, 0)
