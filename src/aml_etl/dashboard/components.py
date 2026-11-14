from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import plotly.graph_objects as go
from dash import dcc, html

from aml_etl.common.formatting import format_decimal
from aml_etl.common.results import StatisticalTest

SMALLEST_REPORTED_P_VALUE = 0.001


@dataclass(frozen=True)
class Badge:
    text: str
    tone: Literal["risk", "ok", "neutral"]


def page_header(title: str, question: str) -> html.Div:
    return html.Div([html.H2(title), html.P(question)], className="ph")


def insight_card(text: str) -> html.Div:
    return html.Div(
        [
            html.Div(html.I(className="icon icon-insight"), className="ic"),
            html.Div([html.Div("Kluczowy wniosek", className="k"), html.Div(text, className="t")]),
        ],
        className="insight",
    )


def kpi_card(
    label: str,
    value: str,
    caption: str,
    badge: Badge | None = None,
    swatch_color: str | None = None,
) -> html.Div:
    label_children: list[html.I | str] = []
    if swatch_color is not None:
        label_children.append(html.I(style={"background": swatch_color}))
    label_children.append(label)
    row: list[html.Div | html.Span] = [html.Div(value, className="v")]
    if badge is not None:
        row.append(html.Span(badge.text, className=f"badge {badge.tone}"))
    return html.Div(
        [
            html.Div(label_children, className="l"),
            html.Div(row, className="row"),
            html.Div(caption, className="s"),
        ],
        className="kpi",
    )


def chart_card(
    title: str,
    subtitle: str,
    figure: go.Figure,
    legend: Sequence[tuple[str, str]] = (),
) -> html.Div:
    legend_items = [
        html.Span([html.I(style={"background": color}), label]) for label, color in legend
    ]
    return html.Div(
        [
            html.Div(
                [
                    html.Div([html.H3(title), html.P(subtitle)]),
                    html.Div(legend_items, className="legend"),
                ],
                className="card-h",
            ),
            dcc.Graph(figure=figure, config={"displayModeBar": False, "responsive": True}),
        ],
        className="card",
    )


def details_table(
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    risk_column: int | None = None,
) -> html.Table:
    header = html.Tr([html.Th(column) for column in columns])
    body = [
        html.Tr(
            [
                html.Td(cell, className="r" if index == risk_column else None)
                for index, cell in enumerate(row)
            ]
        )
        for row in rows
    ]
    return html.Table([html.Thead(header), html.Tbody(body)])


def format_p_value(p_value: float) -> str:
    if p_value < SMALLEST_REPORTED_P_VALUE:
        return "p < 0,001"
    return f"p = {format_decimal(p_value, 3)}"


def format_statistic(statistic: float) -> str:
    return f"{statistic:.3g}".replace(".", ",")


def test_note(test: StatisticalTest, plain_explanation: str) -> html.Div:
    numbers = f" Statystyka = {format_statistic(test.statistic)}, {format_p_value(test.p_value)}. "
    return html.Div(
        [
            html.B(f"Test: {test.name}."),
            numbers,
            plain_explanation,
            html.Div(f"Próba: {test.sample_description}.", className="test-sample"),
        ],
        className="test",
    )


def empty_state(title: str, message: str) -> html.Div:
    return html.Div([html.H3(title), html.P(message)], className="empty-state")
