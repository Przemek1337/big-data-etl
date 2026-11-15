from dash import html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_compact, format_count, format_percent
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
from aml_etl.dashboard.pages.analysis_parts import card, count_bar_figure, number
from aml_etl.dashboard.theme import RISK_COLOR

TITLE = "Banki i konta"
QUESTION = "Czy pranie pieniędzy skupia się w niewielkiej grupie kont i banków nadawców?"
CONCENTRATED_SHARE = 0.25


def render(source: DashboardDataSource, variant: str) -> Component | None:
    result = source.analysis(AnalysisId.BANKS, variant)
    if result is None:
        return None
    banks = result.tables.get("top_banks", [])
    share = number(result, "top_1pct_accounts_laundering_share")
    top_bank = banks[0] if banks else None
    account_count = number(result, "sender_account_count")
    laundering_accounts = number(result, "accounts_with_laundering")
    top_percent_accounts = number(result, "top_1pct_account_count")
    if laundering_accounts <= top_percent_accounts:
        account_share = laundering_accounts / account_count if account_count else 0.0
        concentration = kpi_card(
            "Konta z praniem wśród nadawców",
            format_percent(account_share),
            "tyle kont wysłało choć jedną transakcję prania",
            badge=Badge("silna koncentracja", "risk"),
        )
    else:
        concentration = kpi_card(
            "Udział top 1% kont w praniu",
            format_percent(share, 1),
            f"{format_count(int(top_percent_accounts))} kont nadawców",
            badge=Badge("silna koncentracja", "risk") if share >= CONCENTRATED_SHARE else None,
        )
    kpis = [
        concentration,
        kpi_card(
            "Udział 10 kont z największą liczbą prania",
            format_percent(number(result, "top_10_accounts_laundering_share"), 1),
            "wszystkich transakcji prania",
        ),
        kpi_card(
            "Konta z transakcjami prania",
            format_count(int(number(result, "accounts_with_laundering"))),
            f"z {format_compact(number(result, 'sender_account_count'))} kont nadawców",
        ),
        kpi_card(
            "Bank z największą liczbą prania",
            str(top_bank["bank"]) if top_bank else "brak",
            f"{format_count(int(top_bank['laundering_count']))} transakcji prania"
            if top_bank
            else "brak transakcji prania",
            swatch_color=RISK_COLOR,
        ),
    ]
    table_rows = [
        [
            str(row["bank"]),
            format_count(int(row["transaction_count"])),
            format_count(int(row["laundering_count"])),
            format_percent(float(row["laundering_rate"]), 2),
        ]
        for row in banks
    ]
    return html.Div(
        [
            page_header(TITLE, QUESTION),
            insight_card(result.insight),
            html.Div(kpis, className="kpis"),
            html.Div(
                [
                    chart_card(
                        "Transakcje prania według banku nadawcy",
                        f"{len(banks)} banków z największą liczbą transakcji prania",
                        count_bar_figure(
                            [str(row["bank"]) for row in banks],
                            [int(row["laundering_count"]) for row in banks],
                            RISK_COLOR,
                        ),
                    ),
                    card(
                        "Banki nadawców",
                        "Identyfikatory banków ze zbioru",
                        details_table(["Bank", "Transakcje", "Pranie", "Odsetek"], table_rows, 2),
                    ),
                ],
                className="grid even",
            ),
        ],
        className="page",
    )
