from datetime import date
from pathlib import Path

import pytest

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import RateSource
from aml_etl.rates_scraper.x_rates_page_parser import (
    PageLayoutError,
    XRatesPageParser,
    x_rates_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_x_rates_parser_reads_all_fiat_currencies():
    html = (FIXTURES / "x_rates_2022-09-01.html").read_text(encoding="utf-8")
    rates = XRatesPageParser().parse(html, date(2022, 9, 1), "u")
    by_currency = {r.currency: r for r in rates}
    assert len(rates) == len(by_currency)
    assert set(by_currency) == set(Currency) - {Currency.USD, Currency.BTC}
    assert by_currency[Currency.EUR].usd_per_unit == pytest.approx(1.003908)
    assert 0.006 < by_currency[Currency.JPY].usd_per_unit < 0.008
    assert all(r.source is RateSource.X_RATES and r.rate_date == date(2022, 9, 1) for r in rates)
    assert all(r.source_url == "u" and not r.is_filled for r in rates)


def test_layout_change_raises_page_layout_error():
    with pytest.raises(PageLayoutError):
        XRatesPageParser().parse("<html><body>maintenance</body></html>", date(2022, 9, 1), "u")


def test_non_numeric_rate_raises_page_layout_error():
    html = (
        '<table class="ratesTable"><tbody><tr><td>Euro</td><td>x</td><td>n/a</td></tr>'
        "</tbody></table>"
    )
    with pytest.raises(PageLayoutError):
        XRatesPageParser().parse(html, date(2022, 9, 1), "u")


def test_x_rates_url():
    assert (
        x_rates_url(date(2022, 9, 1))
        == "https://www.x-rates.com/historical/?from=USD&amount=1&date=2022-09-01"
    )
