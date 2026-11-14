from datetime import date, datetime

from selectolax.lexbor import LexborHTMLParser

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource
from aml_etl.rates_scraper.x_rates_page_parser import PageLayoutError

STATMUSE_WINDOW_DAYS = 15
DATE_FORMAT = "%B %d %Y"


def _url_date(value: date) -> str:
    return f"{value.strftime('%B').lower()}-{value.day}-{value.year}"


def statmuse_bitcoin_range_url(start: date, end: date) -> str:
    return (
        "https://www.statmuse.com/money/ask/"
        f"bitcoin-price-from-{_url_date(start)}-to-{_url_date(end)}"
    )


class StatMuseBitcoinPageParser:
    def parse(self, html: str, source_url: str) -> list[ExchangeRate]:
        for table in LexborHTMLParser(html).css("table"):
            headers = [cell.text(strip=True).lower() for cell in table.css("thead th")]
            if "date" in headers and "close" in headers:
                rows = [
                    [cell.text(strip=True) for cell in row.css("td")]
                    for row in table.css("tbody tr")
                ]
                return self._rates(rows, headers.index("date"), headers.index("close"), source_url)
        raise PageLayoutError(f"No table with Date and Close columns at {source_url}")

    def _rates(
        self, rows: list[list[str]], date_column: int, close_column: int, source_url: str
    ) -> list[ExchangeRate]:
        rates: list[ExchangeRate] = []
        for cells in rows:
            if len(cells) <= max(date_column, close_column) or not cells[date_column]:
                continue
            try:
                rate_date = datetime.strptime(cells[date_column], DATE_FORMAT).date()
                close = float(cells[close_column].replace("$", "").replace(",", ""))
            except ValueError as error:
                raise PageLayoutError(
                    f"Unreadable Bitcoin row {cells!r} at {source_url}"
                ) from error
            rates.append(
                ExchangeRate(
                    currency=Currency.BTC,
                    rate_date=rate_date,
                    usd_per_unit=close,
                    source=RateSource.STATMUSE,
                    source_url=source_url,
                )
            )
        if not rates:
            raise PageLayoutError(f"Bitcoin table has no rows at {source_url}")
        return rates
