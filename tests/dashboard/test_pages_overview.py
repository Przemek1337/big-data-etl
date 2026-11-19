from support.dash_tree import collect_text, find_by_class
from support.fake_data_source import FakeDataSource

from aml_etl.common.results import AnalysisId
from aml_etl.dashboard.pages.registry import render_page


def test_overview_page_shows_summary_numbers():
    page = render_page("/", "HI-Medium", FakeDataSource())
    text = collect_text(page)
    assert "Przegląd" in text and "Transakcje" in text and FakeDataSource.AMOUNTS_INSIGHT in text
    assert "W zbiorze HI-Medium 0,11% transakcji to pranie pieniędzy (35 230 z 31,9 mln)." in text
    assert "31,9 mln" in text and "$4,2 bln" in text and "15" in text
    assert len(find_by_class(page, "kpi")) == 4


def test_overview_lists_only_analyses_with_results():
    page = render_page("/", "HI-Medium", FakeDataSource(without=(AnalysisId.AMOUNTS,)))
    assert FakeDataSource.AMOUNTS_INSIGHT not in collect_text(page)
    assert "Przegląd" in collect_text(page)
