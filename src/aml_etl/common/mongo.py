import re
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from aml_etl.common.settings import AmlSettings

CREDENTIALS_PATTERN = re.compile(r"://[^@/]+@")


class DatabaseUnavailableError(RuntimeError):
    pass


def redact_uri(uri: str) -> str:
    return CREDENTIALS_PATTERN.sub("://***@", uri)


class MongoDatabaseFactory:
    def __init__(self, settings: AmlSettings) -> None:
        self._settings = settings

    def local(self) -> Database[dict[str, Any]]:
        return self._connect(self._settings.local_mongo_uri, self._settings.local_database, "local")

    def atlas(self) -> Database[dict[str, Any]]:
        return self._connect(self._settings.atlas_uri, self._settings.atlas_database, "Atlas")

    def _connect(self, uri: str, database: str, label: str) -> Database[dict[str, Any]]:
        try:
            client: MongoClient[dict[str, Any]] = MongoClient(
                uri,
                tz_aware=True,
                serverSelectionTimeoutMS=self._settings.mongo_timeout_ms,
                appname="aml-etl",
            )
            client.admin.command("ping")
        except PyMongoError as error:
            message = f"Cannot reach {label} MongoDB at {redact_uri(uri)}"
            raise DatabaseUnavailableError(message) from error
        return client[database]
