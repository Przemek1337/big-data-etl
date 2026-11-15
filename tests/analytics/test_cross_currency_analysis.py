import pytest
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.cross_currency_analysis import CrossCurrencyAnalysis
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId

VARIANT = DatasetVariant("HI-Small")


def cross(**overrides):
    return transaction_doc(receiving_currency="EUR", is_cross_currency=True, **overrides)


@pytest.mark.integration
def test_cross_currency_analysis(seed):
    docs = [cross(is_laundering=i < 3) for i in range(4)]
    docs += [transaction_doc(is_laundering=i < 1) for i in range(4)]
    result = CrossCurrencyAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert result.analysis_id is AnalysisId.CROSS_CURRENCY
    assert result.metrics["odds_ratio"] == pytest.approx(9.0)
    assert (
        result.insight
        == "Transakcje z przewalutowaniem mają 9,0× większą szansę bycia praniem (iloraz szans)."
    )
    assert result.tables["contingency"] == [
        {
            "is_cross_currency": True,
            "normal_count": 1,
            "laundering_count": 3,
            "laundering_rate": 0.75,
        },
        {
            "is_cross_currency": False,
            "normal_count": 3,
            "laundering_count": 1,
            "laundering_rate": 0.25,
        },
    ]
    assert result.statistical_test is not None


@pytest.mark.integration
def test_cross_currency_without_cross_transactions(seed):
    result = CrossCurrencyAnalysis(lambda: NOW).compute(
        seed([transaction_doc(), transaction_doc()]), VARIANT
    )
    assert result.statistical_test is None
    assert result.insight == "Brak transakcji z przewalutowaniem w tym zbiorze."


@pytest.mark.integration
def test_lower_odds_are_described_as_smaller_chance(seed):
    docs = [cross(is_laundering=i < 1) for i in range(4)]
    docs += [transaction_doc(is_laundering=i < 3) for i in range(4)]
    result = CrossCurrencyAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert (
        result.insight
        == "Transakcje z przewalutowaniem mają 9,0× mniejszą szansę bycia praniem (iloraz szans)."
    )


@pytest.mark.integration
def test_no_laundering_among_cross_currency_transactions(seed):
    docs = [cross() for _ in range(3)] + [transaction_doc(is_laundering=True), transaction_doc()]
    result = CrossCurrencyAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert (
        result.insight
        == "Wśród transakcji z przewalutowaniem nie ma ani jednej oznaczonej jako pranie."
    )
    assert result.metrics["cross_currency_laundering_count"] == 0
