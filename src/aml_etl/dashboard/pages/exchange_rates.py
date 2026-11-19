from collections.abc import Sequence

import plotly.graph_objects as go
from dash import dcc, html
from dash.development.base_component import Component

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource
from aml_etl.common.formatting import format_count
from aml_etl.dashboard.components import (
    details_table,
    empty_state,
    insight_card,
    kpi_card,
    page_header,
)
from aml_etl.dashboard.data_source import DashboardDataSource
from aml_etl.dashboard.figures import style_figure
from aml_etl.dashboard.pages.analysis_parts import card
from aml_etl.dashboard.theme import ACCENT_COLOR, RISK_COLOR

TITLE = "Kursy walut"
QUESTION = "Po jakich kursach przeliczono kwoty transakcji na USD i skąd te kursy pochodzą?"
RATE_CURRENCY_ID = "rate-currency"
RATE_GRAPH_ID = "rate-graph"
DEFAULT_CURRENCY = Currency.EUR.value
DATE_FORMAT = "%d.%m.%Y"
SOURCE_LABELS = {
    RateSource.X_RATES: "x-rates.com",
    RateSource.COINMARKETCAP: "coinmarketcap.com",
    RateSource.FIXED: "stały",
}


def scraped_rates(rates: Sequence[ExchangeRate]) -> list[ExchangeRate]:
    return [rate for rate in rates if rate.source is not RateSource.FIXED]


def rate_figure(rates: Sequence[ExchangeRate], currency: str | None) -> go.Figure:
    selected = sorted(
        (rate for rate in rates if rate.currency.value == currency),
        key=lambda rate: rate.rate_date,
    )
    figure = go.Figure()
    if selected:
        figure.add_trace(
            go.Scatter(
                x=[rate.rate_date for rate in selected],
                y=[rate.usd_per_unit for rate in selected],
                mode="lines+markers",
                line={"color": ACCENT_COLOR, "width": 2},
                marker={
                    "size": 7,
                    "color": [RISK_COLOR if rate.is_filled else ACCENT_COLOR for rate in selected],
                },
                hovertemplate="%{x|%d.%m.%Y}: %{y:,.6g} USD<extra></extra>",
            )
        )
    style_figure(figure)
    figure.update_yaxes(title_text=f"USD za 1 {currency}" if currency else None)
    figure.update_xaxes(tickformat="%d.%m")
    figure.update_layout(margin={"l": 64})
    return figure


def render(source: DashboardDataSource, variant: str) -> Component | None:
    rates = scraped_rates(source.exchange_rates())
    if not rates:
        return html.Div(
            [
                page_header(TITLE, QUESTION),
                empty_state(
                    "Brak kursów walut",
                    "Uruchom serwis rates-scraper (docker compose up), aby pobrać kursy "
                    "z x-rates.com i coinmarketcap.com.",
                ),
            ],
            className="page",
        )
    currencies = sorted({rate.currency.value for rate in rates})
    selected = DEFAULT_CURRENCY if DEFAULT_CURRENCY in currencies else currencies[0]
    days = sorted({rate.rate_date for rate in rates})
    filled = sum(1 for rate in rates if rate.is_filled)
    insight = (
        f"Kursy {format_count(len(currencies))} walut obejmują {format_count(len(days))} dni: "
        f"od {days[0].strftime(DATE_FORMAT)} do {days[-1].strftime(DATE_FORMAT)}. "
        f"Uzupełnionych z sąsiedniego dnia: {format_count(filled)}."
    )
    kpis = [
        kpi_card("Waluty", format_count(len(currencies)), "poza dolarem, który ma stały kurs 1"),
        kpi_card("Dni z kursami", format_count(len(days)), "zakres dat transakcji"),
        kpi_card("Kursy rzeczywiste", format_count(len(rates) - filled), "zczytane ze stron"),
        kpi_card("Kursy uzupełnione", format_count(filled), "przeniesione z sąsiedniego dnia"),
    ]
    selector = dcc.Dropdown(
        id=RATE_CURRENCY_ID,
        options=[{"label": currency, "value": currency} for currency in currencies],
        value=selected,
        clearable=False,
        className="rate-select",
    )
    chart = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Kurs waluty wobec USD"),
                            html.P("Czerwone punkty to dni z kursem uzupełnionym"),
                        ]
                    ),
                    selector,
                ],
                className="card-h",
            ),
            dcc.Graph(
                id=RATE_GRAPH_ID,
                figure=rate_figure(rates, selected),
                config={"displayModeBar": False, "responsive": True},
            ),
        ],
        className="card",
    )
    return html.Div(
        [
            page_header(TITLE, QUESTION),
            insight_card(insight),
            html.Div(kpis, className="kpis"),
            html.Div([chart, _coverage_card(rates, currencies)], className="grid"),
        ],
        className="page",
    )


def _coverage_card(rates: Sequence[ExchangeRate], currencies: Sequence[str]) -> html.Div:
    rows = []
    for currency in currencies:
        own = [rate for rate in rates if rate.currency.value == currency]
        filled = sum(1 for rate in own if rate.is_filled)
        rows.append(
            [
                currency,
                format_count(len(own) - filled),
                format_count(filled),
                SOURCE_LABELS[own[0].source],
            ]
        )
    return card(
        "Pokrycie kursami",
        "Liczba dni z kursem rzeczywistym i uzupełnionym",
        details_table(["Waluta", "Rzeczywiste", "Uzupełnione", "Źródło"], rows),
    )
