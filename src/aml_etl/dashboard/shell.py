from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from dash import dcc, html

Section = Literal["main", "analyses", "data"]

VARIANT_SELECTOR_ID = "variant-selector"
SECTION_LABELS: dict[Section, str | None] = {"main": None, "analyses": "Analizy", "data": "Dane"}
IMPORT_TIME_FORMAT = "%d.%m.%Y, %H:%M"


@dataclass(frozen=True)
class NavItem:
    path: str
    label: str
    section: Section
    icon: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("/", "Przegląd", "main", "overview"),
    NavItem("/kwoty", "Kwoty transakcji", "analyses", "amounts"),
    NavItem("/formy-platnosci", "Formy płatności", "analyses", "payment-formats"),
    NavItem("/czas", "Rozkład w czasie", "analyses", "time"),
    NavItem("/przewalutowania", "Przewalutowania", "analyses", "cross-currency"),
    NavItem("/banki", "Banki i konta", "analyses", "banks"),
    NavItem("/jakosc-danych", "Źródła i jakość", "data", "data-quality"),
    NavItem("/kursy-walut", "Kursy walut", "data", "rates"),
)


def nav_item_for(path: str) -> NavItem | None:
    return next((item for item in NAV_ITEMS if item.path == path), None)


def _nav_links(active_path: str) -> list[html.Div | dcc.Link]:
    links: list[html.Div | dcc.Link] = []
    current_section: Section = "main"
    for item in NAV_ITEMS:
        label = SECTION_LABELS[item.section]
        if item.section != current_section and label is not None:
            links.append(html.Div(label, className="group"))
        current_section = item.section
        links.append(
            dcc.Link(
                [html.I(className=f"icon icon-{item.icon}"), item.label],
                href=item.path,
                className="on" if item.path == active_path else None,
            )
        )
    return links


def sidebar(active_path: str, atlas_connected: bool, last_import_at: datetime | None) -> html.Aside:
    status = "MongoDB Atlas: połączono" if atlas_connected else "MongoDB Atlas: brak połączenia"
    foot: list[html.Span | html.Br | str] = [
        html.Span(className="dot" if atlas_connected else "dot off"),
        status,
    ]
    if last_import_at is not None:
        foot.extend([html.Br(), f"Ostatni import: {last_import_at.strftime(IMPORT_TIME_FORMAT)}"])
    return html.Aside(
        [
            html.Div(
                [
                    html.Div(html.I(className="icon icon-logo"), className="logo"),
                    html.Div([html.B("AML Insight"), html.Small("Analiza transakcji")]),
                ],
                className="brand",
            ),
            html.Nav(_nav_links(active_path), className="nav"),
            html.Div(foot, className="foot"),
        ],
        className="side",
    )


def topbar(breadcrumb: str, variants: Sequence[str], selected: str | None) -> html.Header:
    return html.Header(
        [
            html.Div(html.B(breadcrumb), className="crumb"),
            html.Div(
                dcc.RadioItems(
                    id=VARIANT_SELECTOR_ID,
                    options=[{"label": variant, "value": variant} for variant in variants],
                    value=selected,
                    className="seg",
                    inline=True,
                    persistence=True,
                    persistence_type="session",
                ),
                className="controls",
            ),
        ],
        className="top",
    )
