import logging
from typing import Any, Protocol, Self

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from aml_etl.common.exchange_rates import ExchangeRate, ExchangeRateRepository
from aml_etl.common.mongo import redact_uri
from aml_etl.common.results import AnalysisId, AnalysisResult, DatasetSummary, ResultsRepository
from aml_etl.common.settings import AmlSettings

logger = logging.getLogger(__name__)

DASHBOARD_TIMEOUT_MS = 3_000


class DashboardDataSource(Protocol):
    def is_connected(self) -> bool: ...

    def published_variants(self) -> list[str]: ...

    def summary(self, variant: str) -> DatasetSummary | None: ...

    def analysis(self, analysis_id: AnalysisId, variant: str) -> AnalysisResult | None: ...

    def exchange_rates(self) -> list[ExchangeRate]: ...


class AtlasDashboardDataSource:
    def __init__(self, results: ResultsRepository, rates: ExchangeRateRepository) -> None:
        self._results = results
        self._rates = rates

    @classmethod
    def from_settings(cls, settings: AmlSettings) -> Self:
        client: MongoClient[dict[str, Any]] = MongoClient(
            settings.atlas_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=min(settings.mongo_timeout_ms, DASHBOARD_TIMEOUT_MS),
            connectTimeoutMS=DASHBOARD_TIMEOUT_MS,
            appname="aml-etl-dashboard",
        )
        logger.info("Dashboard reads from %s", redact_uri(settings.atlas_uri))
        database = client[settings.atlas_database]
        return cls(ResultsRepository(database), ExchangeRateRepository(database))

    def is_connected(self) -> bool:
        try:
            self._results.ping()
        except PyMongoError as error:
            logger.warning("MongoDB Atlas is unreachable: %s", type(error).__name__)
            return False
        return True

    def published_variants(self) -> list[str]:
        try:
            return self._results.published_variants()
        except PyMongoError as error:
            logger.warning("Cannot read published variants: %s", type(error).__name__)
            return []

    def summary(self, variant: str) -> DatasetSummary | None:
        try:
            return self._results.summary(variant)
        except PyMongoError as error:
            logger.warning("Cannot read dataset summary: %s", type(error).__name__)
            return None

    def analysis(self, analysis_id: AnalysisId, variant: str) -> AnalysisResult | None:
        try:
            return self._results.analysis(analysis_id, variant)
        except PyMongoError as error:
            logger.warning("Cannot read analysis result: %s", type(error).__name__)
            return None

    def exchange_rates(self) -> list[ExchangeRate]:
        try:
            return self._rates.find_all()
        except PyMongoError as error:
            logger.warning("Cannot read exchange rates: %s", type(error).__name__)
            return []
