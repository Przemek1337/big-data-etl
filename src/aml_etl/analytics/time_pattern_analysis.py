from collections.abc import Callable
from datetime import datetime
from typing import Any

from pymongo.collection import Collection

from aml_etl.analytics.analysis import NO_LAUNDERING_INSIGHT, full_scan
from aml_etl.analytics.statistics import chi_square_test
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.formatting import format_percent
from aml_etl.common.results import AnalysisId, AnalysisResult

Counts = dict[int, tuple[int, int]]

HOURS_PER_DAY = 24
WEEKDAY_LABELS = ("Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz")
SAMPLE_DESCRIPTION = "wszystkie transakcje wariantu, tabela godzina (UTC) × etykieta prania"


class TimePatternAnalysis:
    analysis_id = AnalysisId.TIME_PATTERNS

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult:
        by_hour, by_weekday = self._counts(transactions, variant)
        hour_rows = [self._row("hour", hour, by_hour) for hour in range(HOURS_PER_DAY)]
        weekday_rows = [
            {**self._row("weekday", number, by_weekday), "weekday_label": label}
            for number, label in enumerate(WEEKDAY_LABELS, start=1)
        ]
        has_laundering = any(row["laundering_count"] for row in hour_rows)
        table = [
            [row["transaction_count"] - row["laundering_count"], row["laundering_count"]]
            for row in hour_rows
        ]
        peak = max(hour_rows, key=lambda row: (row["laundering_rate"], -row["hour"]))
        return AnalysisResult(
            analysis_id=self.analysis_id,
            dataset_variant=variant.name,
            insight=self._insight(peak) if has_laundering else NO_LAUNDERING_INSIGHT,
            metrics={
                "peak_hour": int(peak["hour"]),
                "peak_hour_laundering_rate": float(peak["laundering_rate"]),
            },
            tables={"by_hour": hour_rows, "by_weekday": weekday_rows},
            statistical_test=chi_square_test(table, SAMPLE_DESCRIPTION) if has_laundering else None,
            computed_at=self._clock(),
        )

    def _counts(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> tuple[Counts, Counts]:
        moment = {"date": "$timestamp", "timezone": "UTC"}
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {
                "$group": {
                    "_id": {"hour": {"$hour": moment}, "weekday": {"$isoDayOfWeek": moment}},
                    "transaction_count": {"$sum": 1},
                    "laundering_count": {"$sum": {"$cond": ["$is_laundering", 1, 0]}},
                }
            },
        ]
        by_hour: Counts = {}
        by_weekday: Counts = {}
        for group in full_scan(transactions, pipeline):
            counts = (int(group["transaction_count"]), int(group["laundering_count"]))
            for target, key in ((by_hour, "hour"), (by_weekday, "weekday")):
                value = int(group["_id"][key])
                known = target.get(value, (0, 0))
                target[value] = (known[0] + counts[0], known[1] + counts[1])
        return by_hour, by_weekday

    def _row(self, key: str, value: int, counts: Counts) -> dict[str, Any]:
        transaction_count, laundering_count = counts.get(value, (0, 0))
        return {
            key: value,
            "transaction_count": transaction_count,
            "laundering_count": laundering_count,
            "laundering_rate": laundering_count / transaction_count if transaction_count else 0.0,
        }

    def _insight(self, peak: dict[str, Any]) -> str:
        hour = int(peak["hour"])
        end = (hour + 1) % HOURS_PER_DAY
        return (
            f"Najwyższy odsetek prania przypada na godzinę {hour:02d}:00–{end:02d}:00: "
            f"{format_percent(float(peak['laundering_rate']))} transakcji."
        )
