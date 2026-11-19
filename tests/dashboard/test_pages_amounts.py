from support.dash_tree import collect_text, find_by_class, find_by_type
from support.fake_data_source import FakeDataSource

from aml_etl.dashboard.pages.registry import render_page


def test_amounts_page_shows_insight_kpis_and_test():
    page = render_page("/kwoty", "HI-Medium", FakeDataSource())
    text = collect_text(page)
    assert FakeDataSource.AMOUNTS_INSIGHT in text
    assert "Mediana: pranie" in text and "Mann-Whitney U" in text and "P90" in text
    assert "$3 850" in text and "$1 240" in text and "0,34%" in text
    assert "p < 0,001" in text and "istotna" in text
    assert len(find_by_class(page, "kpi")) == 4


def test_amounts_page_chart_has_two_series_on_log_axis():
    [graph] = find_by_type(render_page("/kwoty", "HI-Medium", FakeDataSource()), "Graph")
    assert [trace.name for trace in graph.figure.data] == ["Zwykłe", "Pranie"]
    assert graph.figure.layout.xaxis.type == "log"


def test_amounts_table_marks_laundering_column_as_risk():
    page = render_page("/kwoty", "HI-Medium", FakeDataSource())
    risk_cells = [collect_text(cell) for cell in find_by_class(page, "r")]
    assert risk_cells == ["$410", "$1 190", "$3 850", "$14 200", "$61 500"]


def test_median_labels_point_away_from_each_other():
    [graph] = find_by_type(render_page("/kwoty", "HI-Medium", FakeDataSource()), "Graph")
    anchors = [annotation.xanchor for annotation in graph.figure.layout.annotations]
    assert anchors == ["right", "left"]
