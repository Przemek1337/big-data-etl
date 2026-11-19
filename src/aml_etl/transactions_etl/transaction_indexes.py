import logging
from typing import Any

from pymongo import ASCENDING
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

VARIANT_FIELD = "dataset_variant"
INDEXED_FIELDS = ("is_laundering", "payment_format", "timestamp", "from_bank", "from_account")


class TransactionIndexManager:
    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        self._collection = collection

    def ensure_indexes(self) -> None:
        for field in INDEXED_FIELDS:
            name = self._collection.create_index([(VARIANT_FIELD, ASCENDING), (field, ASCENDING)])
            logger.info("Index ready: %s", name)
