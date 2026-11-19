from collections.abc import Iterator
from typing import Any, Protocol

from pymongo.collection import Collection

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId, AnalysisResult

NO_LAUNDERING_INSIGHT = "W tym wariancie nie ma transakcji oznaczonych jako pranie."

SEQUENTIAL_SCAN_HINT = {"$natural": 1}


def full_scan(
    transactions: Collection[dict[str, Any]], pipeline: list[dict[str, Any]]
) -> Iterator[dict[str, Any]]:
    return iter(transactions.aggregate(pipeline, allowDiskUse=True, hint=SEQUENTIAL_SCAN_HINT))


class Analysis(Protocol):
    analysis_id: AnalysisId

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult: ...
