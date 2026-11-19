from typing import Any

from dash import html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_count, format_percent
from aml_etl.common.results import AnalysisId
from aml_etl.dashboard.components import (
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
    percent_bar_figure,
    significance_kpi,
)
from aml_etl.dashboard.theme import NORMAL_COLOR, RISK_COLOR

TITLE = "Rozkład w czasie"
QUESTION = "Czy pranie pieniędzy skupia się w określonych godzinach lub dniach tygodnia (czas UTC)?"
HOURS_PER_DAY = 24
WEEKDAY_FIGURE_HEIGHT = 220


def _hour_label(hour: int) -> str:
    return f"{hour:02d}:00–{(hour + 1) % HOURS_PER_DAY:02d}:00"


def _peak(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    active = [row for row in rows if int(row["transaction_count"]) > 0]
    return max(active, key=lambda row: float(row["laundering_rate"]), default=None)


def _quietest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    active = [row for row in rows if int(row["transaction_count"]) > 0]
    return min(active, key=lambda row: float(row["laundering_rate"]), default=None)


def _colors(rows: list[dict[str, Any]], peak: dict[str, Any] | None) -> list[str]:
    return [RISK_COLOR if peak is not None and row is peak else NORMAL_COLOR for row in rows]


def render(source: DashboardDataSource, variant: str) -> Component | None:
    result = source.analysis(AnalysisId.TIME_PATTERNS, variant)
    if result is None:
        return None
    hours = result.tables.get("by_hour", [])
    weekdays = result.tables.get("by_weekday", [])
    peak_hour, quiet_hour, peak_day = _peak(hours), _quietest(hours), _peak(weekdays)
    kpis = [
        kpi_card(
            "Godzina z najwyższym odsetkiem",
            _hour_label(int(peak_hour["hour"])) if peak_hour else "brak",
            f"{format_percent(float(peak_hour['laundering_rate']), 3)} transakcji to pranie"
            if peak_hour
            else "brak transakcji",
            swatch_color=RISK_COLOR,
        ),
        kpi_card(
            "Godzina z najniższym odsetkiem",
            _hour_label(int(quiet_hour["hour"])) if quiet_hour else "brak",
            f"{format_percent(float(quiet_hour['laundering_rate']), 3)} transakcji to pranie"
            if quiet_hour
            else "brak transakcji",
            swatch_color=NORMAL_COLOR,
        ),
        kpi_card(
            "Dzień z najwyższym odsetkiem",
            str(peak_day["weekday_label"]) if peak_day else "brak",
            f"{format_percent(float(peak_day['laundering_rate']), 3)} transakcji to pranie"
            if peak_day
            else "brak transakcji",
        ),
        significance_kpi(result.statistical_test, "test chi-kwadrat (godziny)"),
    ]
    weekday_rows = [
        [
            str(row["weekday_label"]),
            format_count(int(row["transaction_count"])),
            format_count(int(row["laundering_count"])),
            format_percent(float(row["laundering_rate"]), 3),
        ]
        for row in weekdays
    ]
    return html.Div(
        [
            page_header(TITLE, QUESTION),
            insight_card(result.insight),
            html.Div(kpis, className="kpis"),
            html.Div(
                [
                    chart_card(
                        "Odsetek prania według godziny",
                        "Udział transakcji oznaczonych jako pranie w każdej godzinie doby",
                        percent_bar_figure(
                            [f"{int(row['hour']):02d}" for row in hours],
                            [float(row["laundering_rate"]) for row in hours],
                            _colors(hours, peak_hour),
                        ),
                        legend=[("Najwyższy odsetek", RISK_COLOR), ("Pozostałe", NORMAL_COLOR)],
                    ),
                    html.Div(
                        [
                            chart_card(
                                "Odsetek prania według dnia tygodnia",
                                "Poniedziałek–niedziela",
                                percent_bar_figure(
                                    [str(row["weekday_label"]) for row in weekdays],
                                    [float(row["laundering_rate"]) for row in weekdays],
                                    _colors(weekdays, peak_day),
                                    height=WEEKDAY_FIGURE_HEIGHT,
                                ),
                            ),
                            card(
                                "Dni tygodnia w liczbach",
                                "Wszystkie transakcje i transakcje prania",
                                details_table(
                                    ["Dzień", "Transakcje", "Pranie", "Odsetek"], weekday_rows
                                ),
                                group_test_note(result.statistical_test),
                            ),
                        ],
                        className="stack",
                    ),
                ],
                className="grid",
            ),
        ],
        className="page",
    )
