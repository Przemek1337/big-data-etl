from dataclasses import dataclass
from typing import Any

import polars as pl
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

DUPLICATE_KEY_CODE = 11000
DEFAULT_CHUNK_ROWS = 25_000


@dataclass(frozen=True)
class LoadResult:
    inserted: int
    already_present: int


class TransactionLoader:
    def __init__(
        self, collection: Collection[dict[str, Any]], chunk_rows: int = DEFAULT_CHUNK_ROWS
    ) -> None:
        self._collection = collection
        self._chunk_rows = chunk_rows

    def load(self, item: pl.DataFrame) -> LoadResult:
        inserted = already_present = 0
        for chunk in item.iter_slices(self._chunk_rows):
            result = self._load_chunk(chunk)
            inserted += result.inserted
            already_present += result.already_present
        return LoadResult(inserted, already_present)

    def _load_chunk(self, chunk: pl.DataFrame) -> LoadResult:
        if chunk.height == 0:
            return LoadResult(0, 0)
        try:
            self._collection.insert_many(chunk.to_dicts(), ordered=False)
        except BulkWriteError as error:
            write_errors = error.details.get("writeErrors", [])
            if any(entry.get("code") != DUPLICATE_KEY_CODE for entry in write_errors):
                raise
            if error.details.get("writeConcernErrors"):
                raise
            return LoadResult(int(error.details.get("nInserted", 0)), len(write_errors))
        return LoadResult(chunk.height, 0)
