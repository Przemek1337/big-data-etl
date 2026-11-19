import pytest
from support.dash_tree import collect_text, find_by_class, find_by_type
from support.fake_data_source import FakeDataSource

from aml_etl.common.results import AnalysisId
from aml_etl.dashboard.pages.data_quality import REJECTION_LABELS
from aml_etl.dashboard.pages.exchange_rates import rate_figure
from aml_etl.dashboard.pages.registry import PAGES, render_page
from aml_etl.dashboard.shell import NAV_ITEMS
from aml_etl.transactions_etl.transaction_cleaner import RejectionReason

ANALYSIS_PAGES = [
    ("/formy-platnosci", FakeDataSource.PAYMENT_FORMATS_INSIGHT, AnalysisId.PAYMENT_FORMATS),
    ("/czas", FakeDataSource.TIME_PATTERNS_INSIGHT, AnalysisId.TIME_PATTERNS),
    ("/przewalutowania", FakeDataSource.CROSS_CURRENCY_INSIGHT, AnalysisId.CROSS_CURRENCY),
    ("/banki", FakeDataSource.BANKS_INSIGHT, AnalysisId.BANKS),
]


def label_for(path: str) -> str:
    return next(item.label for item in NAV_ITEMS if item.path == path)


@pytest.mark.parametrize(("path", "insight", "analysis_id"), ANALYSIS_PAGES)
def test_analysis_page_shows_title_insight_kpis_and_chart(path, insight, analysis_id):
    page = render_page(path, "HI-Medium", FakeDataSource())
    text = collect_text(page)
    assert insight in text and label_for(path) in text
    assert 3 <= len(find_by_class(page, "kpi")) <= 4
    assert find_by_type(page, "Graph") and find_by_type(page, "Table")


@pytest.mark.parametrize(("path", "insight", "analysis_id"), ANALYSIS_PAGES)
def test_analysis_page_without_result_shows_hint(path, insight, analysis_id):
    page = render_page(path, "HI-Medium", FakeDataSource(without=(analysis_id,)))
    assert "Brak wyników tej analizy" in collect_text(page)


def test_payment_formats_page_highlights_riskiest_format():
    page = render_page("/formy-platnosci", "HI-Medium", FakeDataSource())
    text = collect_text(page)
    assert "ACH" in text and "0,79%" in text and "Chi-kwadrat" in text
    [graph] = find_by_type(page, "Graph")
    colors = list(graph.figure.data[0].marker.color)
    assert colors.count("#e5484d") == 1 and set(colors) == {"#e5484d", "#4f6bed"}


def test_time_page_has_hour_and_weekday_charts():
    page = render_page("/czas", "HI-Medium", FakeDataSource())
    graphs = find_by_type(page, "Graph")
    assert [len(graph.figure.data[0].x) for graph in graphs] == [24, 7]
    assert "Ndz" in str(graphs[1].figure.data[0].x)


def test_cross_currency_page_shows_odds_ratio():
    text = collect_text(render_page("/przewalutowania", "HI-Medium", FakeDataSource()))
    assert "Iloraz szans" in text and "0,42" in text
    assert "Z przewalutowaniem" in text and "Bez przewalutowania" in text


def test_banks_page_shows_top_banks_and_concentration():
    page = render_page("/banki", "HI-Medium", FakeDataSource())
    text = collect_text(page)
    assert "42,5%" in text and "070" in text and "2 400" in text
    assert len(find_by_type(page, "Tr")) == 11


def test_data_quality_page_shows_rejections_and_duplicates():
    page = render_page("/jakosc-danych", "HI-Medium", FakeDataSource())
    text = collect_text(page)
    assert "Źródła i jakość" in text
    assert "Nieprawidłowa kwota" in text and "Uszkodzona linia pliku" in text
    assert "31 898 240" in text and "19" in text
    assert "zliczone w obrębie partii importu, pozostawione w danych" in text
    assert "Kaggle" in text and "x-rates.com" in text and "coinmarketcap.com" in text
    assert find_by_class(page, "flow")


def test_data_quality_page_without_published_variant_still_describes_sources():
    text = collect_text(render_page("/jakosc-danych", None, FakeDataSource(variants=[])))
    assert "x-rates.com" in text and "Raport jakości pojawi się po imporcie" in text


def test_unknown_rejection_code_is_shown_as_is():
    source = FakeDataSource()
    summary = source.summary("HI-Medium")
    summary.rejections["brand_new_reason"] = 4
    source.summary = lambda variant: summary
    assert "brand_new_reason" in collect_text(render_page("/jakosc-danych", "HI-Medium", source))


def test_exchange_rates_page_renders_without_published_variants():
    page = render_page("/kursy-walut", None, FakeDataSource(variants=[]))
    text = collect_text(page)
    assert "Kursy walut" in text and "x-rates.com" in text and "coinmarketcap.com" in text
    [dropdown] = find_by_type(page, "Dropdown")
    assert dropdown.value == "EUR"
    assert [option["value"] for option in dropdown.options] == ["BTC", "EUR"]


def test_exchange_rates_table_counts_real_and_filled_days():
    page = render_page("/kursy-walut", None, FakeDataSource(variants=[]))
    rows = [collect_text(row) for row in find_by_type(page, "Tr")]
    assert any(row.startswith("EUR") and row.split()[-3:-1] == ["1", "1"] for row in rows)


def test_exchange_rates_page_without_rates_shows_hint():
    source = FakeDataSource(variants=[])
    source.exchange_rates = lambda: []
    assert "rates-scraper" in collect_text(render_page("/kursy-walut", None, source))


def test_rate_figure_plots_selected_currency_in_date_order():
    figure = rate_figure(FakeDataSource().exchange_rates(), "EUR")
    assert list(figure.data[0].y) == [1.0039, 1.0039]
    assert rate_figure(FakeDataSource().exchange_rates(), "JPY").data == ()


def test_every_rejection_reason_has_polish_label():
    assert set(REJECTION_LABELS) == {reason.value for reason in RejectionReason}


def test_every_nav_item_has_registered_page():
    assert {item.path for item in NAV_ITEMS} == set(PAGES)


def test_only_count_columns_are_marked_as_risk():
    for path in ("/formy-platnosci", "/czas", "/przewalutowania"):
        assert find_by_class(render_page(path, "HI-Medium", FakeDataSource()), "r") == []


def test_banks_page_reports_share_of_accounts_when_top_percent_is_trivial():
    text = collect_text(render_page("/banki", "HI-Medium", FakeDataSource()))
    assert "Konta z praniem wśród nadawców" in text and "0,89%" in text
    assert "Udział top 1% kont w praniu" not in text
