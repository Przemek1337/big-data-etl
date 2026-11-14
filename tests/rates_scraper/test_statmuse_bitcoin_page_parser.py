from datetime import date
from pathlib import Path

import pytest

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import RateSource
from aml_etl.rates_scraper.statmuse_bitcoin_page_parser import (
    StatMuseBitcoinPageParser,
    statmuse_bitcoin_range_url,
)
from aml_etl.rates_scraper.x_rates_page_parser import PageLayoutError

FIXTURES = Path(__file__).parent / "fixtures"


def test_statmuse_parser_reads_close_prices():
    html = (FIXTURES / "statmuse_bitcoin_2022-09.html").read_text(encoding="utf-8")
    parsed = StatMuseBitcoinPageParser().parse(html, "u")
    rates = {r.rate_date: r.usd_per_unit for r in parsed}
    assert rates[date(2022, 9, 30)] == pytest.approx(19431.79)
    assert rates[date(2022, 9, 29)] == pytest.approx(19573.05)
    assert sorted(rates) == [date(2022, 9, day) for day in range(16, 31)]
    assert all(r.currency is Currency.BTC and r.source is RateSource.STATMUSE for r in parsed)


def test_statmuse_layout_change_raises_page_layout_error():
    html = "<table><thead><tr><th>NAME</th></tr></thead><tbody></tbody></table>"
    with pytest.raises(PageLayoutError):
        StatMuseBitcoinPageParser().parse(html, "u")


def test_statmuse_range_url():
    assert (
        statmuse_bitcoin_range_url(date(2022, 8, 25), date(2022, 9, 8))
        == "https://www.statmuse.com/money/ask/bitcoin-price-from-august-25-2022-to-september-8-2022"
    )


def test_hourly_rows_collapse_to_last_price_of_each_day():
    html = (
        "<table><thead><tr><th>DATE</th><th>CLOSE</th></tr></thead><tbody>"
        "<tr><td>September 18 2022 23:00</td><td>$19,409.34</td></tr>"
        "<tr><td>September 18 2022 22:00</td><td>$19,500.00</td></tr>"
        "<tr><td>September 17 2022 23:00</td><td>$20,100.50</td></tr>"
        "</tbody></table>"
    )
    rates = {r.rate_date: r.usd_per_unit for r in StatMuseBitcoinPageParser().parse(html, "u")}
    assert rates == {date(2022, 9, 18): 19409.34, date(2022, 9, 17): 20100.5}
