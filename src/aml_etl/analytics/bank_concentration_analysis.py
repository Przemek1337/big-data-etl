import math
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pymongo.collection import Collection

from aml_etl.analytics.analysis import NO_LAUNDERING_INSIGHT
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.formatting import format_count, format_percent
from aml_etl.common.results import AnalysisId, AnalysisResult

TOP_ACCOUNT_FRACTION = 0.01
TOP_ACCOUNTS_SHOWN = 10


class BankConcentrationAnalysis:
    analysis_id = AnalysisId.BANKS

    def __init__(self, clock: Callable[[], datetime], top_banks: int = 10) -> None:
        self._clock = clock
        self._top_banks = top_banks

    def compute(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> AnalysisResult:
        account_count = self._sender_account_count(transactions, variant)
        laundering_by_account = self._laundering_by_account(transactions, variant)
        laundering_total = sum(laundering_by_account)
        top_accounts = max(1, math.ceil(TOP_ACCOUNT_FRACTION * account_count))
        top_laundering = sum(laundering_by_account[:top_accounts])
        share = top_laundering / laundering_total if laundering_total else 0.0
        laundering_accounts = len(laundering_by_account)
        account_share = laundering_accounts / account_count if account_count else 0.0
        top_ten = sum(laundering_by_account[:TOP_ACCOUNTS_SHOWN])
        if laundering_accounts <= top_accounts:
            insight = (
                f"Wszystkie transakcje prania wychodzą z {format_percent(account_share)} "
                f"kont nadawców ({format_count(laundering_accounts)} "
                f"z {format_count(account_count)})."
            )
        else:
            insight = (
                f"1% kont nadawców odpowiada za {format_percent(share, 1)} "
                "wszystkich transakcji prania."
            )
        return AnalysisResult(
            analysis_id=self.analysis_id,
            dataset_variant=variant.name,
            insight=insight if laundering_total else NO_LAUNDERING_INSIGHT,
            metrics={
                "top_1pct_accounts_laundering_share": share,
                "top_1pct_account_count": top_accounts,
                "accounts_with_laundering": laundering_accounts,
                "laundering_account_share": account_share,
                "top_10_accounts_laundering_share": top_ten / laundering_total
                if laundering_total
                else 0.0,
                "sender_account_count": account_count,
            },
            tables={"top_banks": self._top_bank_rows(transactions, variant)},
            statistical_test=None,
            computed_at=self._clock(),
        )

    def _sender_account_count(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> int:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {"$group": {"_id": "$from_account"}},
            {"$count": "accounts"},
        ]
        result = next(iter(transactions.aggregate(pipeline, allowDiskUse=True)), None)
        return int(result["accounts"]) if result else 0

    def _laundering_by_account(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> list[int]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name, "is_laundering": True}},
            {"$group": {"_id": "$from_account", "laundering_count": {"$sum": 1}}},
            {"$sort": {"laundering_count": -1, "_id": 1}},
        ]
        return [
            int(group["laundering_count"])
            for group in transactions.aggregate(pipeline, allowDiskUse=True)
        ]

    def _top_bank_rows(
        self, transactions: Collection[dict[str, Any]], variant: DatasetVariant
    ) -> list[dict[str, Any]]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"dataset_variant": variant.name}},
            {
                "$group": {
                    "_id": "$from_bank",
                    "transaction_count": {"$sum": 1},
                    "laundering_count": {"$sum": {"$cond": ["$is_laundering", 1, 0]}},
                }
            },
            {"$sort": {"laundering_count": -1, "transaction_count": -1, "_id": 1}},
            {"$limit": self._top_banks},
        ]
        return [
            {
                "bank": str(group["_id"]),
                "transaction_count": int(group["transaction_count"]),
                "laundering_count": int(group["laundering_count"]),
                "laundering_rate": group["laundering_count"] / group["transaction_count"],
            }
            for group in transactions.aggregate(pipeline, allowDiskUse=True)
        ]
