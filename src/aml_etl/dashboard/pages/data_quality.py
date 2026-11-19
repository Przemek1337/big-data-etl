from dash import html
from dash.development.base_component import Component

from aml_etl.common.formatting import format_count, format_percent
from aml_etl.common.results import DatasetSummary
from aml_etl.dashboard.components import (
    Badge,
    details_table,
    empty_state,
    insight_card,
    kpi_card,
    page_header,
)
from aml_etl.dashboard.data_source import DashboardDataSource
from aml_etl.dashboard.pages.analysis_parts import card

TITLE = "Źródła i jakość"
QUESTION = "Skąd pochodzą dane, jak przez system przepływają i ile wierszy odrzucono po drodze?"
KAGGLE_URL = (
    "https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
)
X_RATES_URL = "https://www.x-rates.com/historical/?from=USD&amount=1&date=2022-09-01"
COINMARKETCAP_URL = "https://coinmarketcap.com/historical/20220901/"
REJECTION_LABELS: dict[str, str] = {
    "missing_field": "Brakujące pole",
    "invalid_timestamp": "Nieprawidłowa data",
    "invalid_amount": "Nieprawidłowa kwota",
    "non_positive_amount": "Kwota zerowa lub ujemna",
    "unknown_currency": "Nieznana waluta",
    "unknown_payment_format": "Nieznana forma płatności",
    "invalid_label": "Nieprawidłowa etykieta prania",
    "malformed_line": "Uszkodzona linia pliku",
    "missing_exchange_rate": "Brak kursu waluty na dzień transakcji",
}
DUPLICATES_CAPTION = "zliczone w obrębie partii importu, pozostawione w danych"
FLOW_ROWS: tuple[tuple[str, ...], ...] = (
    ("Kaggle: pliki CSV", "dataset-extractor", "transactions-etl", "MongoDB lokalny: transakcje"),
    ("x-rates.com i coinmarketcap.com", "rates-scraper", "MongoDB Atlas: kursy walut"),
    ("MongoDB lokalny: transakcje", "analytics", "MongoDB Atlas: wyniki", "Dashboard"),
)


def render(source: DashboardDataSource, variant: str) -> Component | None:
    summary = source.summary(variant) if variant else None
    children: list[Component] = [page_header(TITLE, QUESTION)]
    if summary is None:
        children.append(
            empty_state(
                "Brak raportu jakości",
                "Raport jakości pojawi się po imporcie i przeliczeniu analiz (docker compose up).",
            )
        )
    else:
        children.extend(
            [
                insight_card(_insight(summary)),
                html.Div(_kpis(summary), className="kpis"),
            ]
        )
    children.append(
        html.Div([_flow_card(), _rejections_card(summary)], className="grid even"),
    )
    children.append(_sources_card())
    return html.Div(children, className="page")


def _rejection_rate(summary: DatasetSummary) -> float:
    return summary.rows_rejected / summary.rows_read if summary.rows_read else 0.0


def _insight(summary: DatasetSummary) -> str:
    if summary.rows_read == 0:
        return "Import tego wariantu nie zapisał raportu jakości."
    return (
        f"Z {format_count(summary.rows_read)} wczytanych wierszy odrzucono "
        f"{format_count(summary.rows_rejected)} ({format_percent(_rejection_rate(summary), 4)})."
    )


def _kpis(summary: DatasetSummary) -> list[html.Div]:
    clean = summary.rows_rejected == 0
    return [
        kpi_card("Wiersze wczytane", format_count(summary.rows_read), "z pliku źródłowego"),
        kpi_card(
            "Wiersze odrzucone",
            format_count(summary.rows_rejected),
            "nie trafiły do bazy",
            badge=Badge("brak", "ok") if clean else Badge("sprawdź przyczyny", "risk"),
        ),
        kpi_card(
            "Odsetek odrzuceń", format_percent(_rejection_rate(summary), 4), "wszystkich wierszy"
        ),
        kpi_card("Dokładne duplikaty", format_count(summary.duplicate_rows), DUPLICATES_CAPTION),
    ]


def _flow_card() -> html.Div:
    rows = []
    for steps in FLOW_ROWS:
        cells: list[Component] = []
        for index, step in enumerate(steps):
            if index:
                cells.append(html.Span("→", className="flow-arrow"))
            cells.append(html.Span(step, className="flow-step"))
        rows.append(html.Div(cells, className="flow-row"))
    return card(
        "Przepływ danych",
        "Surowe transakcje zostają lokalnie; do Atlasa trafiają tylko kursy i wyniki",
        html.Div(rows, className="flow"),
    )


def _rejections_card(summary: DatasetSummary | None) -> html.Div:
    rejections = summary.rejections if summary else {}
    rows = [
        [REJECTION_LABELS.get(code, code), format_count(count)]
        for code, count in sorted(rejections.items(), key=lambda item: (-item[1], item[0]))
    ]
    if not rows:
        note = "Żaden wiersz nie został odrzucony." if summary else "Brak danych o odrzuceniach."
        return card(
            "Przyczyny odrzuceń", "Każdy wiersz liczony raz", html.P(note, className="note")
        )
    return card(
        "Przyczyny odrzuceń",
        "Każdy wiersz liczony raz, z pierwszą wykrytą przyczyną",
        details_table(["Przyczyna", "Wiersze"], rows, 1),
    )


def _source(name: str, description: str, label: str, url: str) -> html.Li:
    link = html.A(label, href=url, target="_blank", rel="noopener noreferrer")
    return html.Li([html.B(name), f" {description} ", link])


def _sources_card() -> html.Div:
    sources = html.Ul(
        [
            _source(
                "Transakcje.",
                "Syntetyczny zbiór IBM Transactions for Anti Money Laundering, pobierany z",
                "Kaggle",
                KAGGLE_URL,
            ),
            _source(
                "Kursy walut tradycyjnych.",
                "Dzienne kursy wobec USD, zczytywane ze stron historycznych",
                "x-rates.com",
                X_RATES_URL,
            ),
            _source(
                "Kurs Bitcoina.",
                "Dzienna cena w USD, zczytywana z migawek historycznych",
                "coinmarketcap.com",
                COINMARKETCAP_URL,
            ),
        ],
        className="sources",
    )
    return card("Źródła danych", "Trzy źródła zewnętrzne", sources)
