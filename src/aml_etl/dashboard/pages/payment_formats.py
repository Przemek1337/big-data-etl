from dash import html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_count, format_decimal, format_percent
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

TITLE = "Formy płatności"
QUESTION = "Czy któraś forma płatności jest wykorzystywana do prania pieniędzy częściej niż inne?"


def render(source: DashboardDataSource, variant: str) -> Component | None:
    result = source.analysis(AnalysisId.PAYMENT_FORMATS, variant)
    if result is None:
        return None
    rows = result.tables.get("formats", [])
    overall = number(result, "overall_laundering_rate")
    names = [str(row["payment_format"]) for row in rows]
    rates = [float(row["laundering_rate"]) for row in rows]
    top_rate = max(rates, default=0.0)
    colors = [
        RISK_COLOR if index == 0 and rate == top_rate and rate > 0 else NORMAL_COLOR
        for index, rate in enumerate(rates)
    ]
    multiple = top_rate / overall if overall else 0.0
    kpis = [
        kpi_card(
            "Najbardziej ryzykowna forma",
            names[0] if names else "brak",
            f"{format_percent(top_rate)} transakcji to pranie",
            badge=Badge(f"×{format_decimal(multiple)}", "risk") if multiple > 1 else None,
            swatch_color=RISK_COLOR,
        ),
        kpi_card("Średni odsetek prania", format_percent(overall), "we wszystkich formach łącznie"),
        kpi_card("Formy płatności", format_count(len(rows)), "występujące w zbiorze"),
        significance_kpi(result.statistical_test, "test chi-kwadrat"),
    ]
    table_rows = [
        [
            str(row["payment_format"]),
            format_count(int(row["normal_count"])),
            format_count(int(row["laundering_count"])),
            format_percent(float(row["laundering_rate"]), 3),
        ]
        for row in rows
    ]
    return html.Div(
        [
            page_header(TITLE, QUESTION),
            insight_card(result.insight),
            html.Div(kpis, className="kpis"),
            html.Div(
                [
                    chart_card(
                        "Odsetek prania według formy płatności",
                        "Udział transakcji oznaczonych jako pranie; linia przerywana to średnia",
                        percent_bar_figure(names, rates, colors, True, overall),
                        legend=[("Najwyższy odsetek", RISK_COLOR), ("Pozostałe", NORMAL_COLOR)],
                    ),
                    card(
                        "Liczby transakcji",
                        "Zwykłe i oznaczone jako pranie",
                        details_table(["Forma", "Zwykłe", "Pranie", "Odsetek"], table_rows),
                        group_test_note(result.statistical_test),
                    ),
                ],
                className="grid",
            ),
        ],
        className="page",
    )
