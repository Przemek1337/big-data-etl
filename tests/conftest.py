import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from pymongo import MongoClient
from pymongo.database import Database
from testcontainers.community.mongodb import MongoDbContainer

from aml_etl.common.settings import AmlSettings


@pytest.fixture(scope="session")
def mongo_uri() -> Iterator[str]:
    with MongoDbContainer("mongo:7.0") as container:
        yield container.get_connection_url()


@pytest.fixture
def mongo_database(mongo_uri: str) -> Iterator[Database[dict[str, Any]]]:
    client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri, tz_aware=True)
    name = f"test_{uuid.uuid4().hex[:12]}"
    yield client[name]
    client.drop_database(name)
    client.close()


@pytest.fixture
def aml_settings(mongo_uri: str) -> Iterator[AmlSettings]:
    suffix = uuid.uuid4().hex[:12]
    settings = AmlSettings(
        _env_file=None,
        local_mongo_uri=mongo_uri,
        atlas_uri=mongo_uri,
        local_database=f"local_{suffix}",
        atlas_database=f"atlas_{suffix}",
    )
    yield settings
    client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri)
    client.drop_database(settings.local_database)
    client.drop_database(settings.atlas_database)
    client.close()
