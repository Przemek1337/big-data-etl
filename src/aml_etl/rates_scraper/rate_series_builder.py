from collections.abc import Iterable
from dataclasses import replace
from datetime import date

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource
from aml_etl.rates_scraper.date_range import DateRange


class MissingRatesError(RuntimeError):
    pass


class RateSeriesBuilder:
    def complete(
        self,
        rates: Iterable[ExchangeRate],
        date_range: DateRange,
        currencies: Iterable[Currency],
    ) -> list[ExchangeRate]:
        known = self._index(rates)
        completed: list[ExchangeRate] = []
        for currency in currencies:
            if currency is Currency.USD:
                completed.extend(self._fixed_usd(date_range))
                continue
            by_date = known.get(currency, {})
            if not by_date:
                raise MissingRatesError(f"No exchange rate found for {currency.value}")
            completed.extend(self._series(by_date, date_range))
        return completed

    def _index(self, rates: Iterable[ExchangeRate]) -> dict[Currency, dict[date, ExchangeRate]]:
        known: dict[Currency, dict[date, ExchangeRate]] = {}
        for rate in rates:
            by_date = known.setdefault(rate.currency, {})
            current = by_date.get(rate.rate_date)
            if current is None or (current.is_filled and not rate.is_filled):
                by_date[rate.rate_date] = rate
        return known

    def _fixed_usd(self, date_range: DateRange) -> list[ExchangeRate]:
        return [
            ExchangeRate(Currency.USD, day, 1.0, RateSource.FIXED, "") for day in date_range.days()
        ]

    def _series(
        self, by_date: dict[date, ExchangeRate], date_range: DateRange
    ) -> list[ExchangeRate]:
        ordered = sorted(by_date)
        series: list[ExchangeRate] = []
        for day in date_range.days():
            exact = by_date.get(day)
            if exact is not None:
                series.append(exact)
                continue
            earlier = [known_day for known_day in ordered if known_day < day]
            donor_day = earlier[-1] if earlier else ordered[0]
            series.append(replace(by_date[donor_day], rate_date=day, is_filled=True))
        return series
