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
            ExchangeRate(Currency.BTC, date(2022, 9, 1), 20127.14, RateSource.STATMUSE, "u"),
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
