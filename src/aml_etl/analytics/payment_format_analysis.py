from collections.abc import Callable
from datetime import datetime
from typing import Any

from pymongo.collection import Collection

from aml_etl.analytics.analysis import NO_LAUNDERING_INSIGHT
from aml_etl.analytics.statistics import chi_square_test
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.formatting import format_decimal, format_percent
from aml_etl.common.results import AnalysisId, AnalysisResult

SAMPLE_DESCRIPTION = "wszystkie transakcje wariantu, tabela forma płatności × etykieta prania"


class PaymentFormatAnalysis:
    analysis_id = AnalysisId.PAYMENT_FORMATS

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult:
        rows = self._rows(transactions, variant)
        laundering = sum(row["laundering_count"] for row in rows)
        total = laundering + sum(row["normal_count"] for row in rows)
        overall = laundering / total if total else 0.0
        has_laundering = laundering > 0
        table = [[row["normal_count"], row["laundering_count"]] for row in rows]
        return AnalysisResult(
            analysis_id=self.analysis_id,
            dataset_variant=variant.name,
            insight=self._insight(rows, overall) if has_laundering else NO_LAUNDERING_INSIGHT,
            metrics={"overall_laundering_rate": overall, "format_count": len(rows)},
            tables={"formats": rows},
            statistical_test=chi_square_test(table, SAMPLE_DESCRIPTION) if has_laundering else None,
            computed_at=self._clock(),
        )

    def _rows(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> list[dict[str, Any]]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {
                "$group": {
                    "_id": "$payment_format",
                    "normal_count": {"$sum": {"$cond": ["$is_laundering", 0, 1]}},
                    "laundering_count": {"$sum": {"$cond": ["$is_laundering", 1, 0]}},
                }
            },
        ]
        rows = [
            {
                "payment_format": str(group["_id"]),
                "normal_count": int(group["normal_count"]),
                "laundering_count": int(group["laundering_count"]),
                "laundering_rate": group["laundering_count"]
                / (group["normal_count"] + group["laundering_count"]),
            }
            for group in transactions.aggregate(pipeline, allowDiskUse=True)
        ]
        return sorted(rows, key=lambda row: (-row["laundering_rate"], row["payment_format"]))

    def _insight(self, rows: list[dict[str, Any]], overall: float) -> str:
        top = rows[0]
        rate = float(top["laundering_rate"])
        return (
            f"Najwyższy odsetek prania ma forma {top['payment_format']}: "
            f"{format_percent(rate)} transakcji, "
            f"czyli {format_decimal(rate / overall)}× więcej niż średnio."
        )
