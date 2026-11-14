import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from pymongo.database import Database

from aml_etl.common.collections import AtlasCollection

PUBLISHED_VARIANTS_ID = "published_variants"


class AnalysisId(StrEnum):
    AMOUNTS = "amounts"
    PAYMENT_FORMATS = "payment_formats"
    TIME_PATTERNS = "time_patterns"
    CROSS_CURRENCY = "cross_currency"
    BANKS = "banks"


@dataclass(frozen=True)
class StatisticalTest:
    name: str
    statistic: float
    p_value: float
    sample_description: str


@dataclass(frozen=True)
class AnalysisResult:
    analysis_id: AnalysisId
    dataset_variant: str
    insight: str
    metrics: dict[str, float | int | str]
    tables: dict[str, list[dict[str, Any]]]
    statistical_test: StatisticalTest | None
    computed_at: datetime


@dataclass(frozen=True)
class DatasetSummary:
    dataset_variant: str
    transaction_count: int
    laundering_count: int
    laundering_rate: float
    volume_usd: float
    currency_count: int
    period_start: datetime
    period_end: datetime
    rows_read: int
    rows_rejected: int
    rejections: dict[str, int]
    duplicate_rows: int
    last_import_at: datetime | None


class ResultsRepository:
    def __init__(self, database: Database[dict[str, Any]]) -> None:
        self._results = database[AtlasCollection.ANALYSIS_RESULTS]
        self._summaries = database[AtlasCollection.DATASET_SUMMARY]
        self._catalog = database[AtlasCollection.DATASET_CATALOG]
        self._database = database

    def ping(self) -> None:
        self._database.command("ping")

    def publish_variant(self, summary: DatasetSummary, results: Sequence[AnalysisResult]) -> None:
        for result in results:
            document = dataclasses.asdict(result)
            document["analysis_id"] = result.analysis_id.value
            document["_id"] = f"{result.analysis_id.value}:{result.dataset_variant}"
            self._results.replace_one({"_id": document["_id"]}, document, upsert=True)
        summary_document = dataclasses.asdict(summary)
        summary_document["_id"] = summary.dataset_variant
        self._summaries.replace_one({"_id": summary.dataset_variant}, summary_document, upsert=True)

    def set_published_variants(self, variants: Sequence[str], now: datetime) -> None:
        document = {"_id": PUBLISHED_VARIANTS_ID, "variants": list(variants), "updated_at": now}
        self._catalog.replace_one({"_id": PUBLISHED_VARIANTS_ID}, document, upsert=True)

    def published_variants(self) -> list[str]:
        document = self._catalog.find_one({"_id": PUBLISHED_VARIANTS_ID})
        return list(document["variants"]) if document else []

    def summary(self, variant: str) -> DatasetSummary | None:
        document = self._summaries.find_one({"_id": variant})
        if document is None:
            return None
        fields = {field.name: document[field.name] for field in dataclasses.fields(DatasetSummary)}
        return DatasetSummary(**fields)

    def analysis(self, analysis_id: AnalysisId, variant: str) -> AnalysisResult | None:
        document = self._results.find_one({"_id": f"{analysis_id.value}:{variant}"})
        if document is None:
            return None
        test = document["statistical_test"]
        return AnalysisResult(
            analysis_id=AnalysisId(document["analysis_id"]),
            dataset_variant=document["dataset_variant"],
            insight=document["insight"],
            metrics=document["metrics"],
            tables=document["tables"],
            statistical_test=StatisticalTest(**test) if test else None,
            computed_at=document["computed_at"],
        )
