from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import Any

from pymongo import ReplaceOne
from pymongo.database import Database

from aml_etl.common.collections import AtlasCollection
from aml_etl.common.currencies import Currency


class RateSource(StrEnum):
    X_RATES = "x-rates"
    COINMARKETCAP = "coinmarketcap"
    FIXED = "fixed"


@dataclass(frozen=True)
class ExchangeRate:
    currency: Currency
    rate_date: date
    usd_per_unit: float
    source: RateSource
    source_url: str
    is_filled: bool = False


class ExchangeRateRepository:
    def __init__(self, database: Database[dict[str, Any]]) -> None:
        self._collection = database[AtlasCollection.EXCHANGE_RATES]

    def upsert_many(self, rates: Iterable[ExchangeRate]) -> int:
        scraped_at = datetime.now(UTC)
        operations = [
            ReplaceOne({"_id": self._id(rate)}, self._document(rate, scraped_at), upsert=True)
            for rate in rates
        ]
        if not operations:
            return 0
        self._collection.bulk_write(operations, ordered=False)
        return len(operations)

    def find_all(self) -> list[ExchangeRate]:
        return [self._rate(document) for document in self._collection.find({})]

    def scraped_dates(self, source: RateSource) -> set[date]:
        cursor = self._collection.find(
            {"source": source.value, "is_filled": False}, {"rate_date": 1}
        )
        return {document["rate_date"].date() for document in cursor}

    def dates_with_rates(self, currency: Currency) -> set[date]:
        cursor = self._collection.find({"currency": currency.value}, {"rate_date": 1})
        return {document["rate_date"].date() for document in cursor}

    def _id(self, rate: ExchangeRate) -> str:
        return f"{rate.currency.value}:{rate.rate_date.isoformat()}"

    def _document(self, rate: ExchangeRate, scraped_at: datetime) -> dict[str, Any]:
        return {
            "_id": self._id(rate),
            "currency": rate.currency.value,
            "rate_date": datetime.combine(rate.rate_date, time.min, tzinfo=UTC),
            "usd_per_unit": rate.usd_per_unit,
            "source": rate.source.value,
            "source_url": rate.source_url,
            "is_filled": rate.is_filled,
            "scraped_at": scraped_at,
        }

    def _rate(self, document: dict[str, Any]) -> ExchangeRate:
        return ExchangeRate(
            currency=Currency(document["currency"]),
            rate_date=document["rate_date"].date(),
            usd_per_unit=float(document["usd_per_unit"]),
            source=RateSource(document["source"]),
            source_url=document["source_url"],
            is_filled=bool(document["is_filled"]),
        )
