import logging
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from aml_etl.analytics.amount_analysis import AmountAnalysis
from aml_etl.analytics.analysis import Analysis
from aml_etl.analytics.dataset_summary_builder import DatasetSummaryBuilder
from aml_etl.common.collections import LocalCollection
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.results import ResultsRepository
from aml_etl.common.settings import AmlSettings

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def default_analyses(clock: Callable[[], datetime]) -> list[Analysis]:
    return [AmountAnalysis(clock)]


class AnalyticsJob:
    def __init__(
        self,
        analyses: Sequence[Analysis],
        summary_builder: DatasetSummaryBuilder,
        results: ResultsRepository,
        transactions: Collection[dict[str, Any]],
        variants: Sequence[DatasetVariant],
        clock: Callable[[], datetime],
    ) -> None:
        self._analyses = analyses
        self._summary_builder = summary_builder
        self._results = results
        self._transactions = transactions
        self._variants = variants
        self._clock = clock

    def run(self) -> None:
        for variant in self._variants:
            self._publish_variant(variant)
        self._results.set_published_variants(
            [variant.name for variant in self._variants], self._clock()
        )
        logger.info("Published variants: %s", ", ".join(v.name for v in self._variants))

    def _publish_variant(self, variant: DatasetVariant) -> None:
        summary = self._summary_builder.build(variant)
        logger.info(
            "%s: %d transactions, %d laundering",
            variant.name,
            summary.transaction_count,
            summary.laundering_count,
        )
        computed = []
        for analysis in self._analyses:
            started = time.monotonic()
            result = analysis.compute(self._transactions, variant)
            logger.info(
                "%s / %s computed in %.1fs: %s",
                variant.name,
                analysis.analysis_id.value,
                time.monotonic() - started,
                result.insight,
            )
            computed.append(result)
        self._results.publish_variant(summary, computed)


def build_analytics_job(settings: AmlSettings) -> AnalyticsJob:
    factory = MongoDatabaseFactory(settings)
    local = factory.local()
    transactions = local[LocalCollection.TRANSACTIONS]
    return AnalyticsJob(
        analyses=default_analyses(utc_now),
        summary_builder=DatasetSummaryBuilder(
            transactions, local[LocalCollection.DATA_QUALITY], utc_now
        ),
        results=ResultsRepository(factory.atlas()),
        transactions=transactions,
        variants=settings.dataset_variants,
        clock=utc_now,
    )
