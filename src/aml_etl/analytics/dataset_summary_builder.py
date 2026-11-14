from collections.abc import Callable
from datetime import datetime
from typing import Any

from pymongo.collection import Collection

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import DatasetSummary


class NoTransactionsError(RuntimeError):
    pass


class DatasetSummaryBuilder:
    def __init__(
        self,
        transactions: Collection[dict[str, Any]],
        data_quality: Collection[dict[str, Any]],
        clock: Callable[[], datetime],
    ) -> None:
        self._transactions = transactions
        self._data_quality = data_quality
        self._clock = clock

    def build(self, variant: DatasetVariant) -> DatasetSummary:
        totals = self._totals(variant)
        if totals is None or totals["transaction_count"] == 0:
            raise NoTransactionsError(
                f"No transactions for {variant.name} in local MongoDB; run transactions-etl first"
            )
        quality = self._data_quality.find_one({"_id": variant.name}) or {}
        return DatasetSummary(
            dataset_variant=variant.name,
            transaction_count=totals["transaction_count"],
            laundering_count=totals["laundering_count"],
            laundering_rate=totals["laundering_count"] / totals["transaction_count"],
            volume_usd=float(totals["volume_usd"]),
            currency_count=totals["currency_count"],
            period_start=totals["period_start"],
            period_end=totals["period_end"],
            rows_read=int(quality.get("rows_read", 0)),
            rows_rejected=int(quality.get("rows_rejected", 0)),
            rejections=dict(quality.get("rejections", {})),
            duplicate_rows=int(quality.get("exact_duplicate_rows", 0)),
            last_import_at=quality.get("completed_at"),
        )

    def _totals(self, variant: DatasetVariant) -> dict[str, Any] | None:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {
                "$group": {
                    "_id": None,
                    "transaction_count": {"$sum": 1},
                    "laundering_count": {"$sum": {"$cond": ["$is_laundering", 1, 0]}},
                    "volume_usd": {"$sum": "$amount_paid_usd"},
                    "period_start": {"$min": "$timestamp"},
                    "period_end": {"$max": "$timestamp"},
                    "payment_currencies": {"$addToSet": "$payment_currency"},
                    "receiving_currencies": {"$addToSet": "$receiving_currency"},
                }
            },
            {
                "$addFields": {
                    "currency_count": {
                        "$size": {"$setUnion": ["$payment_currencies", "$receiving_currencies"]}
                    }
                }
            },
        ]
        return next(iter(self._transactions.aggregate(pipeline, allowDiskUse=True)), None)
