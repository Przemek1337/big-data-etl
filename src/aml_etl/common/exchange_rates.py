from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from aml_etl.common.currencies import Currency


class RateSource(StrEnum):
    X_RATES = "x-rates"
    STATMUSE = "statmuse"
    FIXED = "fixed"


@dataclass(frozen=True)
class ExchangeRate:
    currency: Currency
    rate_date: date
    usd_per_unit: float
    source: RateSource
    source_url: str
    is_filled: bool = False
