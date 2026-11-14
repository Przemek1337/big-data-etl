from dash import dcc, html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_compact, format_count, format_percent
from aml_etl.common.results import AnalysisId, DatasetSummary
from aml_etl.dashboard.components import (
    Badge,
    empty_state,
    insight_card,
    kpi_card,
    page_header,
)
from aml_etl.dashboard.data_source import DashboardDataSource

TITLE = "Przegląd"
QUESTION = "Najważniejsze liczby o zbiorze i wnioski z poszczególnych analiz."
PERIOD_FORMAT = "%d.%m.%Y"
ANALYSIS_LINKS: tuple[tuple[AnalysisId, str, str], ...] = (
    (AnalysisId.AMOUNTS, "/kwoty", "Kwoty transakcji"),
    (AnalysisId.PAYMENT_FORMATS, "/formy-platnosci", "Formy płatności"),
    (AnalysisId.TIME_PATTERNS, "/czas", "Rozkład w czasie"),
    (AnalysisId.CROSS_CURRENCY, "/przewalutowania", "Przewalutowania"),
    (AnalysisId.BANKS, "/banki", "Banki i konta"),
)


def render(source: DashboardDataSource, variant: str) -> Component | None:
    summary = source.summary(variant)
    if summary is None:
        return empty_state("Brak podsumowania zbioru", "Uruchom ponownie serwis analytics.")
    children: list[Component] = [
        page_header(TITLE, QUESTION),
        insight_card(_insight(summary)),
        html.Div(_kpis(summary), className="kpis"),
    ]
    shortcuts = _shortcuts(source, variant)
    if shortcuts:
        children.append(html.Div(shortcuts, className="grid even"))
    return html.Div(children, className="page")


def _insight(summary: DatasetSummary) -> str:
    return (
        f"W zbiorze {summary.dataset_variant} {format_percent(summary.laundering_rate)} "
        f"transakcji to pranie pieniędzy ({format_count(summary.laundering_count)} "
        f"z {format_compact(summary.transaction_count)})."
    )


def _kpis(summary: DatasetSummary) -> list[html.Div]:
    period = (
        f"{summary.period_start.strftime(PERIOD_FORMAT)} – "
        f"{summary.period_end.strftime(PERIOD_FORMAT)}"
    )
    return [
        kpi_card("Transakcje", format_compact(summary.transaction_count), period),
        kpi_card(
            "Pranie",
            format_count(summary.laundering_count),
            "transakcji oznaczonych jako pranie",
            badge=Badge(format_percent(summary.laundering_rate), "risk"),
        ),
        kpi_card("Wolumen USD", f"${format_compact(summary.volume_usd)}", "suma kwot zapłaconych"),
        kpi_card("Waluty", format_count(summary.currency_count), "przeliczone na USD"),
    ]


def _shortcuts(source: DashboardDataSource, variant: str) -> list[html.Div]:
    cards: list[html.Div] = []
    for analysis_id, path, title in ANALYSIS_LINKS:
        result = source.analysis(analysis_id, variant)
        if result is None:
            continue
        cards.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Div([html.H3(title), html.P(result.insight)]),
                            dcc.Link("Zobacz analizę →", href=path, className="more"),
                        ],
                        className="card-h shortcut",
                    )
                ],
                className="card",
            )
        )
    return cards
