import pytest
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.analytics_job import default_analyses
from aml_etl.analytics.bank_concentration_analysis import BankConcentrationAnalysis
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId

VARIANT = DatasetVariant("HI-Small")


@pytest.mark.integration
def test_bank_concentration(seed):
    docs = [
        transaction_doc(from_account="A0", from_bank="001", is_laundering=i < 3) for i in range(4)
    ]
    docs += [
        transaction_doc(from_account=f"A{n}", from_bank="002", is_laundering=n == 1)
        for n in range(1, 10)
    ]
    result = BankConcentrationAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert result.analysis_id is AnalysisId.BANKS
    assert result.metrics["top_1pct_accounts_laundering_share"] == pytest.approx(0.75)
    assert result.metrics["accounts_with_laundering"] == 2
    assert result.metrics["sender_account_count"] == 10
    assert result.tables["top_banks"] == [
        {"bank": "001", "transaction_count": 4, "laundering_count": 3, "laundering_rate": 0.75},
        {
            "bank": "002",
            "transaction_count": 9,
            "laundering_count": 1,
            "laundering_rate": pytest.approx(1 / 9),
        },
    ]
    assert result.insight == "1% kont nadawców odpowiada za 75,0% wszystkich transakcji prania."


@pytest.mark.integration
def test_top_banks_are_limited(seed):
    docs = [transaction_doc(from_bank=f"{n:03d}", is_laundering=True) for n in range(5)]
    result = BankConcentrationAnalysis(lambda: NOW, top_banks=3).compute(seed(docs), VARIANT)
    assert len(result.tables["top_banks"]) == 3


@pytest.mark.integration
def test_banks_without_laundering(seed):
    result = BankConcentrationAnalysis(lambda: NOW).compute(seed([transaction_doc()]), VARIANT)
    assert result.insight == "W tym wariancie nie ma transakcji oznaczonych jako pranie."
    assert result.metrics["top_1pct_accounts_laundering_share"] == 0.0


def test_default_analyses_cover_every_analysis_id():
    assert {a.analysis_id for a in default_analyses(lambda: NOW)} == set(AnalysisId)


@pytest.mark.integration
def test_when_laundering_fits_in_top_one_percent_the_insight_names_the_real_share(seed):
    docs = [transaction_doc(from_account=f"N{n}") for n in range(398)]
    docs += [transaction_doc(from_account="L1", is_laundering=True) for _ in range(3)]
    docs += [transaction_doc(from_account="L2", is_laundering=True)]
    result = BankConcentrationAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert result.metrics["top_1pct_accounts_laundering_share"] == pytest.approx(1.0)
    assert result.metrics["laundering_account_share"] == pytest.approx(2 / 400)
    assert result.metrics["top_10_accounts_laundering_share"] == pytest.approx(1.0)
    assert result.insight == "Wszystkie transakcje prania wychodzą z 0,50% kont nadawców (2 z 400)."
