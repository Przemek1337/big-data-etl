import plotly.graph_objects as go
from support.dash_tree import collect_text, find_by_class, find_by_type

from aml_etl.common.results import StatisticalTest
from aml_etl.dashboard import components
from aml_etl.dashboard.components import (
    Badge,
    chart_card,
    details_table,
    empty_state,
    insight_card,
    kpi_card,
    page_header,
)
from aml_etl.dashboard.figures import style_figure
from aml_etl.dashboard.theme import FONT_FAMILY


def test_kpi_card_renders_label_value_and_risk_badge():
    card = kpi_card("Mediana: pranie", "$3 850", "35 230 transakcji", badge=Badge("×3,1", "risk"))
    assert "Mediana: pranie" in collect_text(card) and "$3 850" in collect_text(card)
    assert "35 230 transakcji" in collect_text(card)
    assert find_by_class(card, "badge risk")


def test_kpi_card_without_badge_has_no_badge():
    assert not find_by_class(kpi_card("Transakcje", "5", "łącznie"), "badge")


def test_insight_card_has_label_and_text():
    text = collect_text(insight_card("Typowa transakcja prania jest 3,1× większa."))
    assert "Kluczowy wniosek" in text and "3,1×" in text


def test_page_header_shows_title_and_question():
    header = page_header("Kwoty transakcji", "Czy pranie różni się kwotą?")
    assert find_by_class(header, "ph")
    assert "Kwoty transakcji" in collect_text(header) and "Czy pranie" in collect_text(header)


def test_details_table_marks_risk_column():
    table = details_table(["Percentyl", "Zwykłe", "Pranie"], [["P10", "$62", "$410"]], 2)
    assert [collect_text(cell) for cell in find_by_class(table, "r")] == ["$410"]
    assert len(find_by_type(table, "Th")) == 3


def test_chart_card_has_title_legend_and_graph_without_toolbar():
    card = chart_card("Rozkład", "skala log", go.Figure(), legend=[("Zwykłe", "#4f6bed")])
    assert "Rozkład" in collect_text(card) and "Zwykłe" in collect_text(card)
    [graph] = find_by_type(card, "Graph")
    assert graph.config["displayModeBar"] is False


def test_test_note_explains_in_plain_words():
    statistical_test = StatisticalTest("Mann-Whitney U", 12.5, 0.0004, "próba")
    note = components.test_note(statistical_test, "Różnica jest realna.")
    text = collect_text(note)
    assert "Mann-Whitney U" in text and "p < 0,001" in text and "Różnica jest realna." in text
    assert "próba" in text


def test_empty_state():
    state = empty_state("Brak danych", "Uruchom pipeline.")
    assert find_by_class(state, "empty-state") and "Uruchom pipeline." in collect_text(state)


def test_style_figure_applies_theme():
    figure = style_figure(go.Figure())
    assert figure.layout.font.family == FONT_FAMILY
    assert figure.layout.paper_bgcolor == "rgba(0,0,0,0)"


def test_statistic_is_written_without_computer_notation():
    assert components.format_statistic(289064511.5) == "2,89·10⁸"
    assert components.format_statistic(4.1e11) == "4,1·10¹¹"
    assert components.format_statistic(12.5) == "12,5"
    assert components.format_statistic(1234.0) == "1 234"


def test_chart_container_height_follows_figure_height():
    figure = style_figure(go.Figure())
    figure.update_layout(height=220)
    [graph] = find_by_type(chart_card("Dni", "tydzień", figure), "Graph")
    assert graph.style == {"height": "220px"}


def test_figures_use_polish_number_separators():
    assert style_figure(go.Figure()).layout.separators == ", "
