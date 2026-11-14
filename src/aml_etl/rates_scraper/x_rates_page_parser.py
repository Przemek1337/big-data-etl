from datetime import date

from selectolax.lexbor import LexborHTMLParser

from aml_etl.common.currencies import Currency, UnknownCurrencyError
from aml_etl.common.exchange_rates import ExchangeRate, RateSource

NAME_COLUMN = 0
INVERSE_COLUMN = 2


class PageLayoutError(RuntimeError):
    pass


def x_rates_url(rate_date: date) -> str:
    return f"https://www.x-rates.com/historical/?from=USD&amount=1&date={rate_date.isoformat()}"


class XRatesPageParser:
    def parse(self, html: str, rate_date: date, source_url: str) -> list[ExchangeRate]:
        tables = LexborHTMLParser(html).css("table.ratesTable")
        if not tables:
            raise PageLayoutError(f"No ratesTable found at {source_url}")
        rates: dict[Currency, ExchangeRate] = {}
        for table in tables:
            for row in table.css("tbody tr"):
                cells = [cell.text(strip=True) for cell in row.css("td")]
                if len(cells) <= INVERSE_COLUMN:
                    continue
                try:
                    currency = Currency.from_x_rates_name(cells[NAME_COLUMN])
                except UnknownCurrencyError:
                    continue
                if currency in rates:
                    continue
                rates[currency] = ExchangeRate(
                    currency=currency,
                    rate_date=rate_date,
                    usd_per_unit=self._positive_number(cells[INVERSE_COLUMN], source_url),
                    source=RateSource.X_RATES,
                    source_url=source_url,
                )
        return list(rates.values())

    def _positive_number(self, text: str, source_url: str) -> float:
        try:
            value = float(text.replace(",", ""))
        except ValueError as error:
            raise PageLayoutError(f"Unreadable rate {text!r} at {source_url}") from error
        if value <= 0:
            raise PageLayoutError(f"Non-positive rate {text!r} at {source_url}")
        return value
