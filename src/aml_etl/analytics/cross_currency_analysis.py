from collections.abc import Callable
from datetime import datetime
from typing import Any

from pymongo.collection import Collection

from aml_etl.analytics.statistics import chi_square_test, odds_ratio
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.formatting import format_decimal, format_percent
from aml_etl.common.results import AnalysisId, AnalysisResult

SAMPLE_DESCRIPTION = "wszystkie transakcje wariantu, tabela przewalutowanie × etykieta prania"
NO_CROSS_INSIGHT = "Brak transakcji z przewalutowaniem w tym zbiorze."
NO_CROSS_LAUNDERING_INSIGHT = (
    "Wśród transakcji z przewalutowaniem nie ma ani jednej oznaczonej jako pranie."
)


class CrossCurrencyAnalysis:
    analysis_id = AnalysisId.CROSS_CURRENCY

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult:
        counts = self._counts(transactions, variant)
        cross = self._row(True, counts)
        same = self._row(False, counts)
        cross_total = cross["normal_count"] + cross["laundering_count"]
        ratio = odds_ratio(
            [
                [cross["laundering_count"], cross["normal_count"]],
                [same["laundering_count"], same["normal_count"]],
            ]
        )
        table = [
            [cross["normal_count"], cross["laundering_count"]],
            [same["normal_count"], same["laundering_count"]],
        ]
        return AnalysisResult(
            analysis_id=self.analysis_id,
            dataset_variant=variant.name,
            insight=self._insight(cross, same, ratio),
            metrics={
                "odds_ratio": ratio if ratio is not None else 0.0,
                "cross_currency_count": cross_total,
                "cross_currency_laundering_count": cross["laundering_count"],
                "cross_currency_laundering_rate": cross["laundering_rate"],
                "same_currency_laundering_rate": same["laundering_rate"],
            },
            tables={"contingency": [cross, same]},
            statistical_test=chi_square_test(table, SAMPLE_DESCRIPTION) if cross_total else None,
            computed_at=self._clock(),
        )

    def _counts(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> dict[bool, tuple[int, int]]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {
                "$group": {
                    "_id": "$is_cross_currency",
                    "normal_count": {"$sum": {"$cond": ["$is_laundering", 0, 1]}},
                    "laundering_count": {"$sum": {"$cond": ["$is_laundering", 1, 0]}},
                }
            },
        ]
        return {
            bool(group["_id"]): (int(group["normal_count"]), int(group["laundering_count"]))
            for group in transactions.aggregate(pipeline, allowDiskUse=True)
        }

    def _row(self, is_cross: bool, counts: dict[bool, tuple[int, int]]) -> dict[str, Any]:
        normal_count, laundering_count = counts.get(is_cross, (0, 0))
        total = normal_count + laundering_count
        return {
            "is_cross_currency": is_cross,
            "normal_count": normal_count,
            "laundering_count": laundering_count,
            "laundering_rate": laundering_count / total if total else 0.0,
        }

    def _insight(self, cross: dict[str, Any], same: dict[str, Any], ratio: float | None) -> str:
        if cross["normal_count"] + cross["laundering_count"] == 0:
            return NO_CROSS_INSIGHT
        if cross["laundering_count"] == 0:
            return NO_CROSS_LAUNDERING_INSIGHT
        if ratio is None:
            return (
                "Odsetek prania wśród transakcji z przewalutowaniem wynosi "
                f"{format_percent(cross['laundering_rate'])} wobec "
                f"{format_percent(same['laundering_rate'])} bez przewalutowania."
            )
        if ratio >= 1:
            size = f"{format_decimal(ratio)}× większą"
        else:
            size = f"{format_decimal(1 / ratio)}× mniejszą"
        return f"Transakcje z przewalutowaniem mają {size} szansę bycia praniem (iloraz szans)."
