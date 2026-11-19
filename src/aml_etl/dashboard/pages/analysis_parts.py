from collections.abc import Sequence

import plotly.graph_objects as go
from dash import html
from dash.development.base_component import Component

from aml_etl.common.results import AnalysisResult, StatisticalTest
from aml_etl.dashboard.components import Badge, format_p_value, kpi_card, test_note
from aml_etl.dashboard.figures import style_figure
from aml_etl.dashboard.theme import MUTED_COLOR

SIGNIFICANCE_LEVEL = 0.05
PERCENT = 100
DEPENDENT_EXPLANATION = (
    "Test sprawdza, czy odsetek prania jest taki sam we wszystkich grupach. "
    "Tak mała wartość p oznacza, że różnice między grupami nie są dziełem przypadku."
)
INDEPENDENT_EXPLANATION = (
    "Test sprawdza, czy odsetek prania jest taki sam we wszystkich grupach. "
    "Przy takiej wartości p różnic między grupami nie da się odróżnić od przypadku."
)


def number(result: AnalysisResult, key: str) -> float:
    return float(result.metrics.get(key, 0))


def significance_kpi(test: StatisticalTest | None, caption: str) -> html.Div:
    if test is None:
        return kpi_card("Istotność różnic", "brak", "za mało danych do testu")
    significant = test.p_value < SIGNIFICANCE_LEVEL
    badge = Badge("istotne", "ok") if significant else Badge("nieistotne", "neutral")
    return kpi_card("Istotność różnic", format_p_value(test.p_value), caption, badge=badge)


def group_test_note(test: StatisticalTest | None) -> Component | None:
    if test is None:
        return None
    significant = test.p_value < SIGNIFICANCE_LEVEL
    return test_note(test, DEPENDENT_EXPLANATION if significant else INDEPENDENT_EXPLANATION)


def card(title: str, subtitle: str, *children: Component | None) -> html.Div:
    header = html.Div(html.Div([html.H3(title), html.P(subtitle)]), className="card-h")
    return html.Div([header, *[child for child in children if child is not None]], className="card")


def percent_bar_figure(
    categories: Sequence[str],
    rates: Sequence[float],
    colors: Sequence[str],
    horizontal: bool = False,
    average_rate: float | None = None,
    height: int | None = None,
) -> go.Figure:
    values = [rate * PERCENT for rate in rates]
    labels = list(categories)
    bar = go.Bar(
        x=values if horizontal else labels,
        y=labels if horizontal else values,
        orientation="h" if horizontal else "v",
        marker={"color": list(colors)},
        hovertemplate="%{y}: %{x:.3f}%<extra></extra>"
        if horizontal
        else "%{x}: %{y:.3f}%<extra></extra>",
    )
    figure = style_figure(go.Figure(bar))
    line = {"color": MUTED_COLOR, "dash": "dash", "width": 1.2}
    if horizontal:
        figure.update_xaxes(ticksuffix="%", showgrid=True, rangemode="tozero")
        figure.update_yaxes(showgrid=False, autorange="reversed", type="category")
        figure.update_layout(margin={"l": 110})
        if average_rate is not None:
            figure.add_vline(x=average_rate * PERCENT, line=line)
    else:
        figure.update_xaxes(type="category")
        figure.update_yaxes(ticksuffix="%", rangemode="tozero")
        if average_rate is not None:
            figure.add_hline(y=average_rate * PERCENT, line=line)
    if height is not None:
        figure.update_layout(height=height)
    return figure


def count_bar_figure(categories: Sequence[str], counts: Sequence[int], color: str) -> go.Figure:
    bar = go.Bar(
        x=list(categories),
        y=list(counts),
        marker={"color": color},
        hovertemplate="Bank %{x}: %{y} transakcji prania<extra></extra>",
    )
    figure = style_figure(go.Figure(bar))
    figure.update_xaxes(type="category")
    figure.update_yaxes(rangemode="tozero")
    return figure
