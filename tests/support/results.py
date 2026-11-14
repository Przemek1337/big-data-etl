from datetime import UTC, datetime

from aml_etl.common.results import AnalysisId, AnalysisResult, DatasetSummary, StatisticalTest

NOW = datetime(2022, 9, 20, 12, 0, tzinfo=UTC)


def sample_result(analysis_id: AnalysisId, variant: str) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        dataset_variant=variant,
        insight="Mediana kwot prania jest wyższa.",
        metrics={"median_normal_usd": 100.0, "sample_size": 5, "label": "x"},
        tables={"percentiles": [{"percentile": "P10", "normal_usd": 1.0, "laundering_usd": 2.0}]},
        statistical_test=StatisticalTest("Mann-Whitney U", 12.5, 0.01, "co 64. wiersz"),
        computed_at=NOW,
    )


def sample_summary(variant: str) -> DatasetSummary:
    return DatasetSummary(
        dataset_variant=variant,
        transaction_count=10,
        laundering_count=1,
        laundering_rate=0.1,
        volume_usd=1234.5,
        currency_count=15,
        period_start=datetime(2022, 9, 1, tzinfo=UTC),
        period_end=datetime(2022, 9, 18, 16, 18, tzinfo=UTC),
        rows_read=11,
        rows_rejected=1,
        rejections={"invalid_amount": 1},
        duplicate_rows=2,
        last_import_at=NOW,
    )
