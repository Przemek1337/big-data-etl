from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database
from support.results import NOW

from aml_etl.analytics.analysis import Analysis
from aml_etl.analytics.analytics_job import AnalyticsJob, default_analyses
from aml_etl.analytics.dataset_summary_builder import DatasetSummaryBuilder
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId, AnalysisResult, ResultsRepository


def clock():
    return NOW


class ExplodingAnalysis:
    analysis_id = AnalysisId.BANKS

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult:
        raise RuntimeError("analysis exploded")


def build_test_job(
    database: Database[dict[str, Any]],
    variants: list[str],
    extra_analysis: Analysis | None = None,
) -> AnalyticsJob:
    analyses = default_analyses(clock)
    if extra_analysis is not None:
        analyses.append(extra_analysis)
    return AnalyticsJob(
        analyses=analyses,
        summary_builder=DatasetSummaryBuilder(
            database["transactions"], database["data_quality"], clock
        ),
        results=ResultsRepository(database),
        transactions=database["transactions"],
        variants=[DatasetVariant(name) for name in variants],
        clock=clock,
    )
