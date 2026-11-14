from typing import Any, Protocol

from pymongo.collection import Collection

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId, AnalysisResult


class Analysis(Protocol):
    analysis_id: AnalysisId

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult: ...
