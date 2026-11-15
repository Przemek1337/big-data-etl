from typing import Any

from dash import Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component

from aml_etl.dashboard.data_source import DashboardDataSource
from aml_etl.dashboard.pages.exchange_rates import (
    RATE_CURRENCY_ID,
    RATE_GRAPH_ID,
    rate_figure,
    scraped_rates,
)
from aml_etl.dashboard.pages.registry import (
    breadcrumb_for,
    connection_lost_state,
    render_connected_page,
    resolve_variant,
)
from aml_etl.dashboard.shell import BREADCRUMB_ID, VARIANT_SELECTOR_ID, sidebar, topbar
from aml_etl.dashboard.theme import FONT_STYLESHEET

URL_ID = "url"
SIDEBAR_ID = "sidebar-container"
CONTENT_ID = "page-content"
HOME_PATH = "/"


def select_variant(
    current: str | None, source: DashboardDataSource
) -> tuple[list[dict[str, str]], str | None]:
    published = source.published_variants()
    options = [{"label": variant, "value": variant} for variant in published]
    return options, resolve_variant(current, published)


def render_view(
    path: str | None, variant: str | None, source: DashboardDataSource
) -> tuple[Component, str, Component]:
    active_path = path or HOME_PATH
    breadcrumb = breadcrumb_for(active_path)
    if not source.is_connected():
        return sidebar(active_path, False, None), breadcrumb, connection_lost_state()
    active_variant = resolve_variant(variant, source.published_variants())
    summary = source.summary(active_variant) if active_variant else None
    return (
        sidebar(active_path, True, summary.last_import_at if summary else None),
        breadcrumb,
        render_connected_page(active_path, active_variant, source),
    )


def create_app(source: DashboardDataSource) -> Dash:
    app = Dash(
        __name__,
        title="AML Insight",
        external_stylesheets=[FONT_STYLESHEET],
        suppress_callback_exceptions=True,
        update_title="",
    )
    app.layout = html.Div(
        [
            dcc.Location(id=URL_ID),
            html.Div(
                [
                    html.Div(sidebar(HOME_PATH, False, None), id=SIDEBAR_ID),
                    html.Section(
                        [
                            topbar(breadcrumb_for(HOME_PATH), [], None),
                            html.Div(id=CONTENT_ID, className="content"),
                        ],
                        className="main",
                    ),
                ],
                className="app-shell",
            ),
        ]
    )

    @app.callback(
        Output(VARIANT_SELECTOR_ID, "options"),
        Output(VARIANT_SELECTOR_ID, "value"),
        Input(URL_ID, "pathname"),
        State(VARIANT_SELECTOR_ID, "value"),
    )
    def refresh_variants(_: str | None, current: str | None) -> Any:
        return select_variant(current, source)

    @app.callback(
        Output(SIDEBAR_ID, "children"),
        Output(BREADCRUMB_ID, "children"),
        Output(CONTENT_ID, "children"),
        Input(URL_ID, "pathname"),
        Input(VARIANT_SELECTOR_ID, "value"),
    )
    def refresh_view(path: str | None, variant: str | None) -> Any:
        return render_view(path, variant, source)

    @app.callback(
        Output(RATE_GRAPH_ID, "figure"),
        Input(RATE_CURRENCY_ID, "value"),
    )
    def refresh_rate_chart(currency: str | None) -> Any:
        return rate_figure(scraped_rates(source.exchange_rates()), currency)

    return app
