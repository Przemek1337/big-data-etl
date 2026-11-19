from collections.abc import Callable
from dataclasses import dataclass

from dash.development.base_component import Component

from aml_etl.dashboard.components import empty_state
from aml_etl.dashboard.data_source import DashboardDataSource
from aml_etl.dashboard.pages import (
    amounts,
    banks,
    cross_currency,
    data_quality,
    exchange_rates,
    overview,
    payment_formats,
    time_patterns,
)

PageRenderer = Callable[[DashboardDataSource, str], Component | None]


@dataclass(frozen=True)
class Page:
    breadcrumb: str
    renderer: PageRenderer
    needs_published_variant: bool = True


PAGES: dict[str, Page] = {
    "/": Page(overview.TITLE, overview.render),
    "/kwoty": Page(amounts.TITLE, amounts.render),
    "/formy-platnosci": Page(payment_formats.TITLE, payment_formats.render),
    "/czas": Page(time_patterns.TITLE, time_patterns.render),
    "/przewalutowania": Page(cross_currency.TITLE, cross_currency.render),
    "/banki": Page(banks.TITLE, banks.render),
    "/jakosc-danych": Page(data_quality.TITLE, data_quality.render, False),
    "/kursy-walut": Page(exchange_rates.TITLE, exchange_rates.render, False),
}


def breadcrumb_for(path: str) -> str:
    page = PAGES.get(path)
    return page.breadcrumb if page else "Nie ma takiej strony"


def resolve_variant(variant: str | None, published: list[str]) -> str | None:
    if variant in published:
        return variant
    return published[0] if published else None


def connection_lost_state() -> Component:
    return empty_state(
        "Brak połączenia z MongoDB Atlas",
        "Sprawdź ATLAS_URI w pliku .env oraz dostęp sieciowy (Network Access) w Atlasie.",
    )


def render_connected_page(
    path: str, active_variant: str | None, source: DashboardDataSource
) -> Component:
    page = PAGES.get(path)
    if page is None:
        return empty_state("Nie ma takiej strony", "Wybierz pozycję z menu po lewej.")
    if active_variant is None and page.needs_published_variant:
        return empty_state(
            "Brak wyników", "Uruchom pipeline (docker compose up), aby policzyć analizy."
        )
    rendered = page.renderer(source, active_variant or "")
    if rendered is None:
        return empty_state("Brak wyników tej analizy", "Uruchom ponownie serwis analytics.")
    return rendered


def render_page(path: str, variant: str | None, source: DashboardDataSource) -> Component:
    if not source.is_connected():
        return connection_lost_state()
    active_variant = resolve_variant(variant, source.published_variants())
    return render_connected_page(path, active_variant, source)
