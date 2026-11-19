import dataclasses

import pytest
from support.results import NOW, sample_result, sample_summary

from aml_etl.common.results import AnalysisId, ResultsRepository


@pytest.mark.integration
def test_publish_is_idempotent_and_roundtrips(mongo_database):
    repository = ResultsRepository(mongo_database)
    result = sample_result(AnalysisId.AMOUNTS, "HI-Small")
    repository.publish_variant(sample_summary("HI-Small"), [result])
    repository.publish_variant(sample_summary("HI-Small"), [result])
    assert mongo_database["analysis_results"].count_documents({}) == 1
    assert mongo_database["dataset_summary"].count_documents({}) == 1
    assert repository.analysis(AnalysisId.AMOUNTS, "HI-Small") == result
    assert repository.summary("HI-Small") == sample_summary("HI-Small")


@pytest.mark.integration
def test_result_without_test_and_summary_without_import_roundtrip(mongo_database):
    repository = ResultsRepository(mongo_database)
    result = dataclasses.replace(sample_result(AnalysisId.BANKS, "LI-Small"), statistical_test=None)
    summary = dataclasses.replace(sample_summary("LI-Small"), last_import_at=None)
    repository.publish_variant(summary, [result])
    assert repository.analysis(AnalysisId.BANKS, "LI-Small") == result
    assert repository.summary("LI-Small") == summary


@pytest.mark.integration
def test_missing_documents_return_none(mongo_database):
    repository = ResultsRepository(mongo_database)
    assert repository.summary("HI-Small") is None
    assert repository.analysis(AnalysisId.AMOUNTS, "HI-Small") is None


@pytest.mark.integration
def test_published_variants_default_empty_then_replaced(mongo_database):
    repository = ResultsRepository(mongo_database)
    assert repository.published_variants() == []
    repository.set_published_variants(["HI-Small", "LI-Small"], NOW)
    repository.set_published_variants(["HI-Small"], NOW)
    assert repository.published_variants() == ["HI-Small"]
