import pytest
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.payment_format_analysis import PaymentFormatAnalysis
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId

VARIANT = DatasetVariant("HI-Small")


@pytest.mark.integration
def test_payment_format_analysis(seed):
    docs = [transaction_doc(payment_format="ACH", is_laundering=i < 2) for i in range(4)]
    docs += [transaction_doc(payment_format="Cash") for _ in range(4)]
    docs += [transaction_doc(payment_format="Wire", is_laundering=i < 1) for i in range(4)]
    docs += [transaction_doc(dataset_variant="LI-Small", payment_format="Cheque")]
    result = PaymentFormatAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert result.analysis_id is AnalysisId.PAYMENT_FORMATS
    assert [(r["payment_format"], r["laundering_rate"]) for r in result.tables["formats"]] == [
        ("ACH", 0.5),
        ("Wire", 0.25),
        ("Cash", 0.0),
    ]
    assert result.tables["formats"][0] == {
        "payment_format": "ACH",
        "normal_count": 2,
        "laundering_count": 2,
        "laundering_rate": 0.5,
    }
    assert result.metrics["overall_laundering_rate"] == pytest.approx(0.25)
    expected = "Najwyższy odsetek prania ma forma ACH: 50,00% transakcji, czyli 2,0× więcej"
    assert result.insight == f"{expected} niż średnio."
    assert result.statistical_test is not None
    assert result.statistical_test.name == "Chi-kwadrat niezależności"


@pytest.mark.integration
def test_payment_formats_without_laundering(seed):
    docs = [transaction_doc(payment_format="ACH"), transaction_doc(payment_format="Cash")]
    result = PaymentFormatAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert result.statistical_test is None
    assert result.insight == "W tym wariancie nie ma transakcji oznaczonych jako pranie."
