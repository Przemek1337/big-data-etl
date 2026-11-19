from support.dash_tree import collect_text, find_by_class
from support.fake_data_source import FakeDataSource

from aml_etl.common.results import AnalysisId
from aml_etl.dashboard.app import create_app, render_view, select_variant
from aml_etl.dashboard.pages.registry import render_page


def test_atlas_down_renders_connection_empty_state():
    text = collect_text(render_page("/kwoty", "HI-Medium", FakeDataSource(connected=False)))
    assert "Brak połączenia z MongoDB Atlas" in text and "ATLAS_URI" in text


def test_no_published_variants_renders_pipeline_hint():
    text = collect_text(render_page("/kwoty", None, FakeDataSource(variants=[])))
    assert "docker compose up" in text


def test_unknown_path_renders_not_found():
    assert "Nie ma takiej strony" in collect_text(
        render_page("/xyz", "HI-Medium", FakeDataSource())
    )


def test_missing_analysis_result_renders_hint():
    source = FakeDataSource(without=(AnalysisId.AMOUNTS,))
    text = collect_text(render_page("/kwoty", "HI-Medium", source))
    assert "Brak wyników tej analizy" in text and "analytics" in text


def test_unpublished_variant_falls_back_to_first_published():
    text = collect_text(render_page("/kwoty", "HI-Large", FakeDataSource()))
    assert FakeDataSource.AMOUNTS_INSIGHT in text


def test_create_app_builds_layout():
    app = create_app(FakeDataSource())
    layout = str(app.layout)
    assert app.title == "AML Insight" and "page-content" in layout
    assert "variant-selector" in layout and "app-shell" in layout


def test_render_view_marks_active_page_and_breadcrumb():
    side, breadcrumb, content = render_view("/kwoty", "HI-Medium", FakeDataSource())
    assert "Kwoty transakcji" in collect_text(find_by_class(side, "on")[0])
    assert breadcrumb == "Kwoty transakcji"
    assert "Ostatni import: 27.10.2026, 21:14" in collect_text(side)
    assert FakeDataSource.AMOUNTS_INSIGHT in collect_text(content)


def test_render_view_without_path_shows_overview():
    _, breadcrumb, content = render_view(None, None, FakeDataSource())
    assert breadcrumb == "Przegląd" and "Transakcje" in collect_text(content)


def test_select_variant_keeps_valid_choice_and_defaults_to_first():
    source = FakeDataSource()
    assert select_variant("LI-Medium", source) == (
        [
            {"label": "HI-Medium", "value": "HI-Medium"},
            {"label": "LI-Medium", "value": "LI-Medium"},
        ],
        "LI-Medium",
    )
    assert select_variant("HI-Large", source)[1] == "HI-Medium"
    assert select_variant(None, FakeDataSource(variants=[])) == ([], None)


def test_disconnected_view_asks_the_database_only_once():
    source = FakeDataSource(connected=False)
    side, _, content = render_view("/kwoty", "HI-Medium", source)
    assert source.calls == ["is_connected"]
    assert "MongoDB Atlas: brak połączenia" in collect_text(side)
    assert "Brak połączenia z MongoDB Atlas" in collect_text(content)


def test_connected_view_pings_once():
    source = FakeDataSource()
    render_view("/kwoty", "HI-Medium", source)
    assert source.calls.count("is_connected") == 1
