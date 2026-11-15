from typing import Any, Protocol

from pymongo.collection import Collection

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId, AnalysisResult

NO_LAUNDERING_INSIGHT = "W tym wariancie nie ma transakcji oznaczonych jako pranie."


class Analysis(Protocol):
    analysis_id: AnalysisId

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult: ...
