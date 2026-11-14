from datetime import date

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource

EUR = Currency.EUR
BTC = Currency.BTC


def rate(currency: Currency, day: int, value: float, filled: bool = False) -> ExchangeRate:
    source = RateSource.STATMUSE if currency is Currency.BTC else RateSource.X_RATES
    return ExchangeRate(currency, date(2022, 9, day), value, source, "u", filled)
