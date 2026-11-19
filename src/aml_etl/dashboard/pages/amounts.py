import math
from typing import Any

import plotly.graph_objects as go
from dash import html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_compact, format_decimal, format_percent, format_usd
from aml_etl.common.results import AnalysisId, AnalysisResult, StatisticalTest
from aml_etl.dashboard.components import (
    Badge,
    chart_card,
    details_table,
    format_p_value,
    insight_card,
    kpi_card,
    page_header,
    test_note,
)
from aml_etl.dashboard.data_source import DashboardDataSource
from aml_etl.dashboard.figures import style_figure
from aml_etl.dashboard.theme import NORMAL_COLOR, RISK_COLOR

TITLE = "Kwoty transakcji"
QUESTION = (
    "Czy transakcje oznaczone jako pranie pieniędzy różnią się kwotą od zwykłych? "
    "Wszystkie kwoty przeliczono na USD po kursach z dnia transakcji."
)
SIGNIFICANCE_LEVEL = 0.05
SIGNIFICANT_EXPLANATION = (
    "Test sprawdza, czy kwoty w jednej grupie są systematycznie większe niż w drugiej. "
    "Tak mała wartość p oznacza, że różnica nie jest dziełem przypadku."
)
INSIGNIFICANT_EXPLANATION = (
    "Test sprawdza, czy kwoty w jednej grupie są systematycznie większe niż w drugiej. "
    "Przy takiej wartości p różnicy nie da się odróżnić od przypadku."
)
AXIS_TICKS = {
    0.01: "$0,01",
    0.1: "$0,1",
    1: "$1",
    10: "$10",
    100: "$100",
    1e3: "$1k",
    1e4: "$10k",
    1e5: "$100k",
    1e6: "$1M",
    1e7: "$10M",
    1e8: "$100M",
    1e9: "$1G",
    1e10: "$10G",
    1e11: "$100G",
    1e12: "$1T",
}


def render(source: DashboardDataSource, variant: str) -> Component | None:
    result = source.analysis(AnalysisId.AMOUNTS, variant)
    if result is None:
        return None
    return html.Div(
        [
            page_header(TITLE, QUESTION),
            insight_card(result.insight),
            html.Div(_kpis(result), className="kpis"),
            html.Div(
                [
                    chart_card(
                        "Rozkład kwot transakcji",
                        "Udział transakcji w przedziale kwot, oś pozioma logarytmiczna (USD)",
                        _distribution_figure(result),
                        legend=[("Zwykłe", NORMAL_COLOR), ("Pranie", RISK_COLOR)],
                    ),
                    _percentile_card(result),
                ],
                className="grid",
            ),
        ],
        className="page",
    )


def _number(result: AnalysisResult, key: str) -> float:
    return float(result.metrics.get(key, 0))


def _kpis(result: AnalysisResult) -> list[html.Div]:
    normal_count = int(_number(result, "normal_count"))
    laundering_count = int(_number(result, "laundering_count"))
    total = normal_count + laundering_count
    count_share = laundering_count / total if total else 0.0
    volume_share = _number(result, "laundering_volume_share")
    ratio = _number(result, "median_ratio")
    ratio_badge = Badge(f"×{format_decimal(ratio)}", "risk" if ratio >= 1 else "neutral")
    return [
        kpi_card(
            "Mediana: zwykłe",
            format_usd(_number(result, "median_normal_usd")),
            f"{format_compact(normal_count)} transakcji",
            swatch_color=NORMAL_COLOR,
        ),
        kpi_card(
            "Mediana: pranie",
            format_usd(_number(result, "median_laundering_usd")),
            f"{format_compact(laundering_count)} transakcji",
            badge=ratio_badge if laundering_count else None,
            swatch_color=RISK_COLOR,
        ),
        kpi_card(
            "Udział prania w wolumenie",
            format_percent(volume_share),
            f"przy {format_percent(count_share)} liczby transakcji",
            badge=_volume_badge(volume_share, count_share),
        ),
        _significance_kpi(result.statistical_test),
    ]


def _volume_badge(volume_share: float, count_share: float) -> Badge | None:
    if count_share <= 0:
        return None
    multiple = volume_share / count_share
    if multiple >= 1:
        return Badge(f"{format_decimal(multiple)}× ponad liczbę", "risk")
    return Badge(f"{format_decimal(multiple)}× liczby", "neutral")


def _significance_kpi(test: StatisticalTest | None) -> html.Div:
    if test is None:
        return kpi_card("Istotność różnicy", "brak", "za mało danych do testu")
    significant = test.p_value < SIGNIFICANCE_LEVEL
    badge = Badge("istotna", "ok") if significant else Badge("nieistotna", "neutral")
    return kpi_card(
        "Istotność różnicy", format_p_value(test.p_value), "test Manna-Whitneya U", badge=badge
    )


def _shares(rows: list[dict[str, Any]], key: str) -> list[float]:
    total = sum(int(row[key]) for row in rows)
    return [100 * int(row[key]) / total if total else 0.0 for row in rows]


def _distribution_figure(result: AnalysisResult) -> go.Figure:
    rows = result.tables.get("histogram", [])
    centers = [math.sqrt(row["bin_start_usd"] * row["bin_end_usd"]) for row in rows]
    figure = go.Figure()
    series = (
        ("Zwykłe", "normal_count", NORMAL_COLOR, "rgba(79,107,237,0.14)"),
        ("Pranie", "laundering_count", RISK_COLOR, "rgba(229,72,77,0.14)"),
    )
    for name, key, color, fill in series:
        figure.add_trace(
            go.Scatter(
                x=centers,
                y=_shares(rows, key),
                name=name,
                mode="lines",
                line={"color": color, "width": 2, "shape": "spline"},
                fill="tozeroy",
                fillcolor=fill,
                hovertemplate="%{y:.1f}% transakcji<extra>" + name + "</extra>",
            )
        )
    normal_median = _number(result, "median_normal_usd")
    laundering_median = _number(result, "median_laundering_usd")
    normal_is_lower = normal_median <= laundering_median
    medians = (
        (normal_median, NORMAL_COLOR, "right" if normal_is_lower else "left"),
        (laundering_median, RISK_COLOR, "left" if normal_is_lower else "right"),
    )
    for median, color, anchor in medians:
        if median > 0:
            figure.add_vline(x=median, line={"color": color, "dash": "dash", "width": 1.5})
            figure.add_annotation(
                x=math.log10(median),
                y=1.0,
                yref="paper",
                yanchor="bottom",
                xanchor=anchor,
                xshift=-3 if anchor == "right" else 3,
                text=f"<b>{format_usd(median)}</b>",
                showarrow=False,
                font={"color": "#ffffff", "size": 11},
                bgcolor=color,
                borderpad=4,
            )
    style_figure(figure)
    visible = [
        value for value in AXIS_TICKS if not centers or min(centers) <= value <= max(centers)
    ]
    figure.update_xaxes(
        type="log", tickvals=visible, ticktext=[AXIS_TICKS[value] for value in visible]
    )
    figure.update_yaxes(ticksuffix="%", rangemode="tozero")
    figure.update_layout(margin={"t": 34})
    return figure


def _usd_cell(value: Any) -> str:
    return format_usd(float(value)) if value is not None else "–"


def _percentile_card(result: AnalysisResult) -> html.Div:
    rows = [
        [row["percentile"], _usd_cell(row["normal_usd"]), _usd_cell(row["laundering_usd"])]
        for row in result.tables.get("percentiles", [])
    ]
    children: list[Component] = [
        html.Div(
            html.Div([html.H3("Percentyle kwot (USD)"), html.P("Porównanie obu grup")]),
            className="card-h",
        ),
        details_table(["Percentyl", "Zwykłe", "Pranie"], rows, risk_column=2),
    ]
    test = result.statistical_test
    if test is not None:
        significant = test.p_value < SIGNIFICANCE_LEVEL
        explanation = SIGNIFICANT_EXPLANATION if significant else INSIGNIFICANT_EXPLANATION
        children.append(test_note(test, explanation))
    return html.Div(children, className="card")
