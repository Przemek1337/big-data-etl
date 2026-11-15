from datetime import date
from pathlib import Path

import pytest

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import RateSource
from aml_etl.rates_scraper.coinmarketcap_page_parser import (
    CoinMarketCapPageParser,
    coinmarketcap_url,
)
from aml_etl.rates_scraper.x_rates_page_parser import PageLayoutError

FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2022, 9, 1)


def table(header_cells: str, body_rows: str) -> str:
    return f"<table><thead><tr>{header_cells}</tr></thead><tbody>{body_rows}</tbody></table>"


def test_reads_bitcoin_price_from_snapshot_page():
    html = (FIXTURES / "coinmarketcap_2022-09-01.html").read_text(encoding="utf-8")
    [rate] = CoinMarketCapPageParser().parse(html, DAY, "u")
    assert rate.currency is Currency.BTC and rate.rate_date == DAY
    assert rate.usd_per_unit == pytest.approx(20127.14)
    assert rate.source is RateSource.COINMARKETCAP and rate.source_url == "u"
    assert not rate.is_filled


def test_finds_bitcoin_row_by_symbol_not_by_position():
    html = table(
        "<th>Rank</th><th>Price</th><th>Symbol</th>",
        "<tr><td>1</td><td>$1,577.64</td><td>ETH</td></tr>"
        "<tr><td>2</td><td>$19,986.71</td><td>BTC</td></tr>",
    )
    [rate] = CoinMarketCapPageParser().parse(html, DAY, "u")
    assert rate.usd_per_unit == pytest.approx(19986.71)


def test_page_without_snapshot_table_raises_layout_error():
    with pytest.raises(PageLayoutError, match="Symbol and Price"):
        CoinMarketCapPageParser().parse("<html><body>Just a moment...</body></html>", DAY, "u")


def test_snapshot_without_bitcoin_row_raises_layout_error():
    html = table("<th>Symbol</th><th>Price</th>", "<tr><td>ETH</td><td>$1.00</td></tr>")
    with pytest.raises(PageLayoutError, match="BTC"):
        CoinMarketCapPageParser().parse(html, DAY, "u")


def test_unreadable_price_raises_layout_error():
    html = table("<th>Symbol</th><th>Price</th>", "<tr><td>BTC</td><td>n/a</td></tr>")
    with pytest.raises(PageLayoutError):
        CoinMarketCapPageParser().parse(html, DAY, "u")


def test_snapshot_url():
    assert coinmarketcap_url(date(2022, 9, 4)) == "https://coinmarketcap.com/historical/20220904/"
