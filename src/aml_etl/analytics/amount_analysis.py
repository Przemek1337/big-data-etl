from collections.abc import Callable
from datetime import datetime
from typing import Any

from pymongo.collection import Collection
from scipy import stats

from aml_etl.analytics.analysis import NO_LAUNDERING_INSIGHT, full_scan
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.formatting import format_decimal, format_usd
from aml_etl.common.results import AnalysisId, AnalysisResult, StatisticalTest

PERCENTILES = (("P10", 0.1), ("P25", 0.25), ("Mediana", 0.5), ("P75", 0.75), ("P90", 0.9))
MEDIAN_INDEX = 2
BINS_PER_DECADE = 4
MANN_WHITNEY_NAME = "Mann-Whitney U"
NO_NORMAL_INSIGHT = "W tym wariancie są wyłącznie transakcje oznaczone jako pranie."


class AmountAnalysis:
    analysis_id = AnalysisId.AMOUNTS

    def __init__(self, clock: Callable[[], datetime], normal_sample_modulus: int = 64) -> None:
        self._clock = clock
        self._normal_sample_modulus = normal_sample_modulus

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult:
        groups = self._groups(transactions, variant)
        normal, laundering = groups.get(False), groups.get(True)
        normal_volume = float(normal["volume_usd"]) if normal else 0.0
        laundering_volume = float(laundering["volume_usd"]) if laundering else 0.0
        total_volume = normal_volume + laundering_volume
        median_normal = self._median(normal)
        median_laundering = self._median(laundering)
        metrics: dict[str, float | int | str] = {
            "median_normal_usd": median_normal,
            "median_laundering_usd": median_laundering,
            "median_ratio": median_laundering / median_normal if median_normal else 0.0,
            "normal_count": int(normal["count"]) if normal else 0,
            "laundering_count": int(laundering["count"]) if laundering else 0,
            "laundering_volume_share": laundering_volume / total_volume if total_volume else 0.0,
        }
        both_present = normal is not None and laundering is not None
        return AnalysisResult(
            analysis_id=self.analysis_id,
            dataset_variant=variant.name,
            insight=self._insight(normal, laundering, median_normal, median_laundering),
            metrics=metrics,
            tables={
                "percentiles": self._percentile_table(normal, laundering),
                "histogram": self._histogram(transactions, variant),
            },
            statistical_test=self._mann_whitney(transactions, variant) if both_present else None,
            computed_at=self._clock(),
        )

    def _groups(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> dict[bool, dict[str, Any]]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {
                "$group": {
                    "_id": "$is_laundering",
                    "count": {"$sum": 1},
                    "volume_usd": {"$sum": "$amount_paid_usd"},
                    "percentiles": {
                        "$percentile": {
                            "input": "$amount_paid_usd",
                            "p": [fraction for _, fraction in PERCENTILES],
                            "method": "approximate",
                        }
                    },
                }
            },
        ]
        return {bool(group["_id"]): group for group in full_scan(transactions, pipeline)}

    def _median(self, group: dict[str, Any] | None) -> float:
        return float(group["percentiles"][MEDIAN_INDEX]) if group else 0.0

    def _percentile_table(
        self, normal: dict[str, Any] | None, laundering: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        return [
            {
                "percentile": label,
                "normal_usd": float(normal["percentiles"][index]) if normal else None,
                "laundering_usd": float(laundering["percentiles"][index]) if laundering else None,
            }
            for index, (label, _) in enumerate(PERCENTILES)
        ]

    def _histogram(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> list[dict[str, Any]]:
        bin_index = {"$floor": {"$multiply": [{"$log10": "$amount_paid_usd"}, BINS_PER_DECADE]}}
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name, "amount_paid_usd": {"$gt": 0}}},
            {
                "$group": {
                    "_id": bin_index,
                    "normal_count": {"$sum": {"$cond": ["$is_laundering", 0, 1]}},
                    "laundering_count": {"$sum": {"$cond": ["$is_laundering", 1, 0]}},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        return [
            {
                "bin_start_usd": 10 ** (int(row["_id"]) / BINS_PER_DECADE),
                "bin_end_usd": 10 ** ((int(row["_id"]) + 1) / BINS_PER_DECADE),
                "normal_count": int(row["normal_count"]),
                "laundering_count": int(row["laundering_count"]),
            }
            for row in full_scan(transactions, pipeline)
        ]

    def _test_samples(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> tuple[list[float], list[float]]:
        sampled_row = {"row_number": {"$mod": [self._normal_sample_modulus, 0]}}
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "dataset_variant": variant.name,
                    "$or": [{"is_laundering": True}, sampled_row],
                }
            },
            {"$project": {"_id": 0, "amount_paid_usd": 1, "is_laundering": 1}},
        ]
        laundering: list[float] = []
        normal: list[float] = []
        for document in full_scan(transactions, pipeline):
            target = laundering if document["is_laundering"] else normal
            target.append(float(document["amount_paid_usd"]))
        return laundering, normal

    def _mann_whitney(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> StatisticalTest | None:
        laundering, normal = self._test_samples(transactions, variant)
        if not laundering or not normal:
            return None
        result = stats.mannwhitneyu(laundering, normal, alternative="two-sided")
        description = (
            f"pranie: wszystkie {len(laundering)} transakcji; zwykłe: co "
            f"{self._normal_sample_modulus}. wiersz pliku źródłowego, {len(normal)} transakcji"
        )
        return StatisticalTest(
            name=MANN_WHITNEY_NAME,
            statistic=float(result.statistic),
            p_value=float(result.pvalue),
            sample_description=description,
        )

    def _insight(
        self,
        normal: dict[str, Any] | None,
        laundering: dict[str, Any] | None,
        median_normal: float,
        median_laundering: float,
    ) -> str:
        if laundering is None:
            return NO_LAUNDERING_INSIGHT
        if normal is None:
            return NO_NORMAL_INSIGHT
        medians = f"(mediana {format_usd(median_laundering)} wobec {format_usd(median_normal)})"
        if median_laundering >= median_normal:
            ratio, direction = median_laundering / median_normal, "większa"
        else:
            ratio, direction = median_normal / median_laundering, "mniejsza"
        size = f"{format_decimal(ratio)}× {direction}"
        return f"Typowa transakcja prania jest {size} od zwykłej {medians}."
