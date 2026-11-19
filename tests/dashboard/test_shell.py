from datetime import UTC, datetime

from support.dash_tree import collect_text, find_by_class, find_by_type

from aml_etl.dashboard.shell import NAV_ITEMS, sidebar, topbar


def test_sidebar_marks_active_item_and_connection_state():
    side = sidebar("/kwoty", atlas_connected=False, last_import_at=None)
    active = find_by_class(side, "on")
    assert len(active) == 1 and "Kwoty transakcji" in collect_text(active[0])
    assert "MongoDB Atlas: brak połączenia" in collect_text(side)
    assert find_by_class(side, "dot off")


def test_sidebar_shows_connection_and_import_time():
    side = sidebar("/", True, datetime(2026, 10, 27, 21, 14, tzinfo=UTC))
    text = collect_text(side)
    assert "MongoDB Atlas: połączono" in text and "Ostatni import: 27.10.2026, 21:14" in text
    assert "Analizy" in text and "Dane" in text


def test_nav_paths():
    assert [i.path for i in NAV_ITEMS] == [
        "/",
        "/kwoty",
        "/formy-platnosci",
        "/czas",
        "/przewalutowania",
        "/banki",
        "/jakosc-danych",
        "/kursy-walut",
    ]


def test_topbar_has_breadcrumb_and_variant_selector():
    bar = topbar("Kwoty transakcji", ["HI-Small", "LI-Small"], "LI-Small")
    assert "Kwoty transakcji" in collect_text(bar)
    [selector] = find_by_type(bar, "RadioItems")
    assert selector.id == "variant-selector" and selector.value == "LI-Small"
    assert [option["value"] for option in selector.options] == ["HI-Small", "LI-Small"]


def test_topbar_without_variants_keeps_selector_empty():
    [selector] = find_by_type(topbar("Przegląd", [], None), "RadioItems")
    assert selector.options == [] and selector.value is None


def test_import_time_is_labelled_as_utc():
    side = sidebar("/", True, datetime(2026, 10, 27, 21, 14, tzinfo=UTC))
    assert "Ostatni import: 27.10.2026, 21:14 UTC" in collect_text(side)
