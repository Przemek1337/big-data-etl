from datetime import date

from selectolax.lexbor import LexborHTMLParser

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource
from aml_etl.rates_scraper.x_rates_page_parser import PageLayoutError

SYMBOL_HEADER = "symbol"
PRICE_HEADER = "price"
BITCOIN_SYMBOL = "BTC"


def coinmarketcap_url(rate_date: date) -> str:
    return f"https://coinmarketcap.com/historical/{rate_date.strftime('%Y%m%d')}/"


class CoinMarketCapPageParser:
    def parse(self, html: str, rate_date: date, source_url: str) -> list[ExchangeRate]:
        snapshot_found = False
        for table in LexborHTMLParser(html).css("table"):
            headers = [cell.text(strip=True).lower() for cell in table.css("thead th")]
            if SYMBOL_HEADER not in headers or PRICE_HEADER not in headers:
                continue
            snapshot_found = True
            symbol_column = headers.index(SYMBOL_HEADER)
            price_column = headers.index(PRICE_HEADER)
            for row in table.css("tbody tr"):
                cells = [cell.text(strip=True) for cell in row.css("td")]
                if len(cells) <= max(symbol_column, price_column):
                    continue
                if cells[symbol_column] == BITCOIN_SYMBOL:
                    price = self._price(cells[price_column], source_url)
                    return [
                        ExchangeRate(
                            currency=Currency.BTC,
                            rate_date=rate_date,
                            usd_per_unit=price,
                            source=RateSource.COINMARKETCAP,
                            source_url=source_url,
                        )
                    ]
        if not snapshot_found:
            raise PageLayoutError(f"No table with Symbol and Price columns at {source_url}")
        raise PageLayoutError(f"No BTC row in the snapshot table at {source_url}")

    def _price(self, text: str, source_url: str) -> float:
        try:
            value = float(text.replace("$", "").replace(",", ""))
        except ValueError as error:
            raise PageLayoutError(f"Unreadable Bitcoin price {text!r} at {source_url}") from error
        if value <= 0:
            raise PageLayoutError(f"Non-positive Bitcoin price {text!r} at {source_url}")
        return value
