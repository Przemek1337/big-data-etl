from collections.abc import Callable
from typing import Any

import pytest
from pymongo.collection import Collection
from pymongo.database import Database

Seed = Callable[[list[dict[str, Any]]], Collection[dict[str, Any]]]


@pytest.fixture
def seed(mongo_database: Database[dict[str, Any]]) -> Seed:
    def insert(documents: list[dict[str, Any]]) -> Collection[dict[str, Any]]:
        collection = mongo_database["transactions"]
        if documents:
            collection.insert_many(documents)
        return collection

    return insert
