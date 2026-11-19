from datetime import UTC, date, datetime

from aml_etl.common.currencies import Currency
from aml_etl.common.exchange_rates import ExchangeRate, RateSource
from aml_etl.common.results import (
    AnalysisId,
    AnalysisResult,
    DatasetSummary,
    StatisticalTest,
)

COMPUTED_AT = datetime(2026, 10, 27, 21, 30, tzinfo=UTC)


class FakeDataSource:
    AMOUNTS_INSIGHT = (
        "Typowa transakcja prania jest 3,1× większa od zwykłej (mediana $3 850 wobec $1 240)."
    )

    def __init__(
        self,
        connected: bool = True,
        variants: list[str] | None = None,
        without: tuple[AnalysisId, ...] = (),
    ) -> None:
        self._connected = connected
        self._variants = ["HI-Medium", "LI-Medium"] if variants is None else variants
        self._without = without
        self.calls: list[str] = []

    def is_connected(self) -> bool:
        self.calls.append("is_connected")
        return self._connected

    def published_variants(self) -> list[str]:
        self.calls.append("published_variants")
        return list(self._variants) if self._connected else []

    def summary(self, variant: str) -> DatasetSummary | None:
        self.calls.append("summary")
        if not self._connected or variant not in self._variants:
            return None
        return DatasetSummary(
            dataset_variant=variant,
            transaction_count=31_898_238,
            laundering_count=35_230,
            laundering_rate=35_230 / 31_898_238,
            volume_usd=4.2e12,
            currency_count=15,
            period_start=datetime(2022, 9, 1, tzinfo=UTC),
            period_end=datetime(2022, 9, 28, 15, 58, tzinfo=UTC),
            rows_read=31_898_240,
            rows_rejected=2,
            rejections={"invalid_amount": 1, "malformed_line": 1},
            duplicate_rows=19,
            last_import_at=datetime(2026, 10, 27, 21, 14, tzinfo=UTC),
        )

    def analysis(self, analysis_id: AnalysisId, variant: str) -> AnalysisResult | None:
        self.calls.append("analysis")
        if not self._connected or variant not in self._variants or analysis_id in self._without:
            return None
        builder = getattr(self, f"_{analysis_id.value}", None)
        return builder(variant) if builder else None

    def exchange_rates(self) -> list[ExchangeRate]:
        self.calls.append("exchange_rates")
        if not self._connected:
            return []
        return [
            ExchangeRate(Currency.EUR, date(2022, 9, 1), 1.0039, RateSource.X_RATES, "u"),
            ExchangeRate(Currency.EUR, date(2022, 9, 2), 1.0039, RateSource.X_RATES, "u", True),
            ExchangeRate(Currency.BTC, date(2022, 9, 1), 20127.14, RateSource.COINMARKETCAP, "u"),
            ExchangeRate(Currency.USD, date(2022, 9, 1), 1.0, RateSource.FIXED, ""),
        ]

    def _amounts(self, variant: str) -> AnalysisResult:
        return AnalysisResult(
            analysis_id=AnalysisId.AMOUNTS,
            dataset_variant=variant,
            insight=self.AMOUNTS_INSIGHT,
            metrics={
                "median_normal_usd": 1240.0,
                "median_laundering_usd": 3850.0,
                "median_ratio": 3.1,
                "normal_count": 31_863_008,
                "laundering_count": 35_230,
                "laundering_volume_share": 0.0034,
            },
            tables={
                "percentiles": [
                    {"percentile": "P10", "normal_usd": 62.0, "laundering_usd": 410.0},
                    {"percentile": "P25", "normal_usd": 318.0, "laundering_usd": 1190.0},
                    {"percentile": "Mediana", "normal_usd": 1240.0, "laundering_usd": 3850.0},
                    {"percentile": "P75", "normal_usd": 5870.0, "laundering_usd": 14200.0},
                    {"percentile": "P90", "normal_usd": 24100.0, "laundering_usd": 61500.0},
                ],
                "histogram": [
                    {
                        "bin_start_usd": 10 ** (k / 4),
                        "bin_end_usd": 10 ** ((k + 1) / 4),
                        "normal_count": 1000 * (12 - abs(k - 12)),
                        "laundering_count": 10 * (14 - abs(k - 14)),
                    }
                    for k in range(4, 22)
                ],
            },
            statistical_test=StatisticalTest(
                "Mann-Whitney U", 4.1e11, 1e-12, "pranie: wszystkie 35230 transakcji"
            ),
            computed_at=COMPUTED_AT,
        )

    PAYMENT_FORMATS_INSIGHT = (
        "Najwyższy odsetek prania ma forma ACH: 0,79% transakcji, czyli 7,2× więcej niż średnio."
    )
    TIME_PATTERNS_INSIGHT = (
        "Najwyższy odsetek prania przypada na godzinę 12:00–13:00: 0,21% transakcji."
    )
    CROSS_CURRENCY_INSIGHT = (
        "Transakcje z przewalutowaniem mają 2,4× mniejszą szansę bycia praniem (iloraz szans)."
    )
    BANKS_INSIGHT = "1% kont nadawców odpowiada za 42,5% wszystkich transakcji prania."

    def _result(
        self,
        analysis_id: AnalysisId,
        variant: str,
        insight: str,
        metrics: dict[str, float | int | str],
        tables: dict[str, list[dict[str, object]]],
        with_test: bool = True,
    ) -> AnalysisResult:
        test = StatisticalTest("Chi-kwadrat niezależności", 1234.5, 1e-9, "wszystkie transakcje")
        return AnalysisResult(
            analysis_id=analysis_id,
            dataset_variant=variant,
            insight=insight,
            metrics=metrics,
            tables=tables,
            statistical_test=test if with_test else None,
            computed_at=COMPUTED_AT,
        )

    def _payment_formats(self, variant: str) -> AnalysisResult:
        formats = [
            ("ACH", 3_970_000, 31_600, 0.0079),
            ("Bitcoin", 990_000, 510, 0.0005),
            ("Cheque", 12_100_000, 2_300, 0.0002),
            ("Credit Card", 8_400_000, 700, 0.0001),
            ("Cash", 3_100_000, 120, 0.00004),
            ("Reinvestment", 3_000_000, 0, 0.0),
            ("Wire", 1_100_000, 0, 0.0),
        ]
        rows = [
            {
                "payment_format": name,
                "normal_count": normal,
                "laundering_count": laundering,
                "laundering_rate": rate,
            }
            for name, normal, laundering, rate in formats
        ]
        metrics = {"overall_laundering_rate": 0.0011, "format_count": 7}
        return self._result(
            AnalysisId.PAYMENT_FORMATS,
            variant,
            self.PAYMENT_FORMATS_INSIGHT,
            metrics,
            {"formats": rows},
        )

    def _time_patterns(self, variant: str) -> AnalysisResult:
        by_hour = [
            {
                "hour": hour,
                "transaction_count": 1_000_000 + 10_000 * hour,
                "laundering_count": 900 + 100 * (12 - abs(hour - 12)),
                "laundering_rate": 0.0009 + 0.0001 * (12 - abs(hour - 12)),
            }
            for hour in range(24)
        ]
        labels = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
        by_weekday = [
            {
                "weekday": number,
                "weekday_label": label,
                "transaction_count": 4_000_000,
                "laundering_count": 4_000 + 300 * number,
                "laundering_rate": 0.001 + 0.00007 * number,
            }
            for number, label in enumerate(labels, start=1)
        ]
        metrics = {"peak_hour": 12, "peak_hour_laundering_rate": 0.0021}
        return self._result(
            AnalysisId.TIME_PATTERNS,
            variant,
            self.TIME_PATTERNS_INSIGHT,
            metrics,
            {"by_hour": by_hour, "by_weekday": by_weekday},
        )

    def _cross_currency(self, variant: str) -> AnalysisResult:
        contingency = [
            {
                "is_cross_currency": True,
                "normal_count": 452_000,
                "laundering_count": 210,
                "laundering_rate": 0.00046,
            },
            {
                "is_cross_currency": False,
                "normal_count": 31_411_008,
                "laundering_count": 35_020,
                "laundering_rate": 0.00111,
            },
        ]
        metrics = {
            "odds_ratio": 0.417,
            "cross_currency_count": 452_210,
            "cross_currency_laundering_count": 210,
            "cross_currency_laundering_rate": 0.00046,
            "same_currency_laundering_rate": 0.00111,
        }
        return self._result(
            AnalysisId.CROSS_CURRENCY,
            variant,
            self.CROSS_CURRENCY_INSIGHT,
            metrics,
            {"contingency": contingency},
        )

    def _banks(self, variant: str) -> AnalysisResult:
        top_banks = [
            {
                "bank": f"0{70 + n}",
                "transaction_count": 900_000 - 50_000 * n,
                "laundering_count": 2_400 - 200 * n,
                "laundering_rate": (2_400 - 200 * n) / (900_000 - 50_000 * n),
            }
            for n in range(10)
        ]
        metrics = {
            "top_1pct_accounts_laundering_share": 0.425,
            "top_1pct_account_count": 20_500,
            "accounts_with_laundering": 18_300,
            "sender_account_count": 2_050_000,
        }
        return self._result(
            AnalysisId.BANKS,
            variant,
            self.BANKS_INSIGHT,
            metrics,
            {"top_banks": top_banks},
            with_test=False,
        )
