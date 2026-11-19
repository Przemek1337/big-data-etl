import pytest
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.amount_analysis import AmountAnalysis
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId

VARIANT = DatasetVariant("HI-Small")


@pytest.mark.integration
def test_amount_analysis(seed):
    docs = [transaction_doc(amount_paid_usd=v) for v in (100, 200, 300, 400, 500)]
    docs += [transaction_doc(amount_paid_usd=v, is_laundering=True) for v in (1000, 2000, 3000)]
    docs += [transaction_doc(dataset_variant="LI-Small", amount_paid_usd=9e9)]
    result = AmountAnalysis(lambda: NOW, normal_sample_modulus=1).compute(seed(docs), VARIANT)
    assert result.analysis_id is AnalysisId.AMOUNTS and result.dataset_variant == "HI-Small"
    assert result.metrics["median_normal_usd"] == pytest.approx(300, rel=0.05)
    assert result.metrics["median_laundering_usd"] == pytest.approx(2000, rel=0.05)
    assert (result.metrics["normal_count"], result.metrics["laundering_count"]) == (5, 3)
    assert result.metrics["laundering_volume_share"] == pytest.approx(6000 / 7500)
    assert (
        result.insight
        == "Typowa transakcja prania jest 6,7× większa od zwykłej (mediana $2 000 wobec $300)."
    )
    assert result.statistical_test.name == "Mann-Whitney U"
    assert result.statistical_test.p_value < 0.05
    assert [r["percentile"] for r in result.tables["percentiles"]] == [
        "P10",
        "P25",
        "Mediana",
        "P75",
        "P90",
    ]
    histogram = result.tables["histogram"]
    assert sum(r["normal_count"] for r in histogram) == 5
    assert sum(r["laundering_count"] for r in histogram) == 3
    assert [r["bin_start_usd"] for r in histogram] == sorted(r["bin_start_usd"] for r in histogram)
    assert histogram[0]["bin_start_usd"] == pytest.approx(100.0)
    assert histogram[0]["bin_end_usd"] == pytest.approx(10**2.25)


@pytest.mark.integration
def test_smaller_laundering_amounts_reverse_the_sentence(seed):
    docs = [transaction_doc(amount_paid_usd=1000.0) for _ in range(3)]
    docs += [transaction_doc(amount_paid_usd=250.0, is_laundering=True) for _ in range(3)]
    result = AmountAnalysis(lambda: NOW, normal_sample_modulus=1).compute(seed(docs), VARIANT)
    assert (
        result.insight
        == "Typowa transakcja prania jest 4,0× mniejsza od zwykłej (mediana $250 wobec $1 000)."
    )


@pytest.mark.integration
def test_normal_sample_takes_every_nth_row(seed):
    docs = [transaction_doc(amount_paid_usd=100.0) for _ in range(8)]
    docs += [transaction_doc(is_laundering=True)]
    result = AmountAnalysis(lambda: NOW, normal_sample_modulus=4).compute(seed(docs), VARIANT)
    description = result.statistical_test.sample_description
    assert "co 4. wiersz pliku źródłowego, 2 transakcji" in description
    assert "pranie: wszystkie 1 transakcji" in description


@pytest.mark.integration
def test_variant_without_laundering_has_no_test_and_says_so(seed):
    result = AmountAnalysis(lambda: NOW).compute(seed([transaction_doc()]), VARIANT)
    assert result.statistical_test is None
    assert result.insight == "W tym wariancie nie ma transakcji oznaczonych jako pranie."
    assert result.metrics["laundering_count"] == 0
