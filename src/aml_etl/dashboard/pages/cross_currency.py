from dash import html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_compact, format_count, format_decimal, format_percent
from aml_etl.common.results import AnalysisId
from aml_etl.dashboard.components import (
    Badge,
    chart_card,
    details_table,
    insight_card,
    kpi_card,
    page_header,
)
from aml_etl.dashboard.data_source import DashboardDataSource
from aml_etl.dashboard.pages.analysis_parts import (
    card,
    group_test_note,
    number,
    percent_bar_figure,
    significance_kpi,
)
from aml_etl.dashboard.theme import NORMAL_COLOR, RISK_COLOR

TITLE = "Przewalutowania"
QUESTION = (
    "Czy transakcje, w których waluta zapłaty różni się od waluty otrzymanej, "
    "częściej są praniem pieniędzy?"
)
CROSS_LABEL = "Z przewalutowaniem"
SAME_LABEL = "Bez przewalutowania"
FIGURE_HEIGHT = 260


def render(source: DashboardDataSource, variant: str) -> Component | None:
    result = source.analysis(AnalysisId.CROSS_CURRENCY, variant)
    if result is None:
        return None
    rows = result.tables.get("contingency", [])
    labels = [CROSS_LABEL if row["is_cross_currency"] else SAME_LABEL for row in rows]
    rates = [float(row["laundering_rate"]) for row in rows]
    cross_rate = number(result, "cross_currency_laundering_rate")
    same_rate = number(result, "same_currency_laundering_rate")
    odds = number(result, "odds_ratio")
    cross_is_riskier = cross_rate > same_rate
    colors = [
        RISK_COLOR if (label == CROSS_LABEL) == cross_is_riskier else NORMAL_COLOR
        for label in labels
    ]
    odds_badge = None
    if odds > 0:
        odds_badge = Badge("większa szansa", "risk") if odds > 1 else Badge("mniejsza", "ok")
    kpis = [
        kpi_card(
            "Odsetek prania: z przewalutowaniem",
            format_percent(cross_rate, 3),
            f"{format_compact(number(result, 'cross_currency_count'))} transakcji",
            swatch_color=colors[labels.index(CROSS_LABEL)] if CROSS_LABEL in labels else None,
        ),
        kpi_card(
            "Odsetek prania: bez przewalutowania",
            format_percent(same_rate, 3),
            "ta sama waluta po obu stronach",
            swatch_color=colors[labels.index(SAME_LABEL)] if SAME_LABEL in labels else None,
        ),
        kpi_card(
            "Iloraz szans",
            format_decimal(odds, 2) if odds > 0 else "brak",
            "szansa prania z przewalutowaniem wobec bez",
            badge=odds_badge,
        ),
        significance_kpi(result.statistical_test, "test chi-kwadrat 2×2"),
    ]
    table_rows = [
        [
            label,
            format_count(int(row["normal_count"])),
            format_count(int(row["laundering_count"])),
            format_percent(float(row["laundering_rate"]), 3),
        ]
        for label, row in zip(labels, rows, strict=True)
    ]
    return html.Div(
        [
            page_header(TITLE, QUESTION),
            insight_card(result.insight),
            html.Div(kpis, className="kpis"),
            html.Div(
                [
                    chart_card(
                        "Odsetek prania a przewalutowanie",
                        "Udział transakcji oznaczonych jako pranie w obu grupach",
                        percent_bar_figure(labels, rates, colors, height=FIGURE_HEIGHT),
                    ),
                    card(
                        "Tabela liczebności",
                        "Podstawa testu i ilorazu szans",
                        details_table(["Grupa", "Zwykłe", "Pranie", "Odsetek"], table_rows),
                        group_test_note(result.statistical_test),
                    ),
                ],
                className="grid even",
            ),
        ],
        className="page",
    )
