import pytest
from support.analytics_jobs import ExplodingAnalysis, build_test_job
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.analytics_job import default_analyses
from aml_etl.analytics.dataset_summary_builder import NoTransactionsError
from aml_etl.common.results import ResultsRepository


@pytest.mark.integration
def test_job_publishes_all_results_idempotently(seed, mongo_database):
    seed(
        [
            transaction_doc(is_laundering=True),
            transaction_doc(),
            transaction_doc(receiving_currency="EUR", is_cross_currency=True),
        ]
    )
    job = build_test_job(mongo_database, ["HI-Small"])
    job.run()
    job.run()
    expected = len(default_analyses(lambda: NOW))
    assert mongo_database["analysis_results"].count_documents({}) == expected
    assert mongo_database["dataset_summary"].count_documents({}) == 1
    assert ResultsRepository(mongo_database).published_variants() == ["HI-Small"]


@pytest.mark.integration
def test_failing_analysis_publishes_nothing_for_variant(seed, mongo_database):
    seed([transaction_doc(is_laundering=True), transaction_doc()])
    with pytest.raises(RuntimeError, match="exploded"):
        build_test_job(mongo_database, ["HI-Small"], extra_analysis=ExplodingAnalysis()).run()
    assert mongo_database["analysis_results"].count_documents({}) == 0
    assert mongo_database["dataset_summary"].count_documents({}) == 0


@pytest.mark.integration
def test_variant_without_transactions_fails_without_publishing(seed, mongo_database):
    seed([])
    with pytest.raises(NoTransactionsError):
        build_test_job(mongo_database, ["HI-Small"]).run()
    assert ResultsRepository(mongo_database).published_variants() == []
