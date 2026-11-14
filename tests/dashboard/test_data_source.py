import pytest
from pymongo.errors import ServerSelectionTimeoutError
from support.results import sample_result, sample_summary

from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.common.results import AnalysisId, ResultsRepository
from aml_etl.common.settings import AmlSettings
from aml_etl.dashboard.data_source import AtlasDashboardDataSource


class BrokenResults:
    def published_variants(self):
        raise ServerSelectionTimeoutError("down")

    def summary(self, variant):
        raise ServerSelectionTimeoutError("down")

    def analysis(self, analysis_id, variant):
        raise ServerSelectionTimeoutError("down")

    def ping(self):
        raise ServerSelectionTimeoutError("down")


class BrokenRates:
    def find_all(self):
        raise ServerSelectionTimeoutError("down")


def test_data_source_survives_mongo_errors():
    source = AtlasDashboardDataSource(BrokenResults(), BrokenRates())
    assert source.published_variants() == [] and source.exchange_rates() == []
    assert source.summary("HI-Small") is None
    assert source.analysis(AnalysisId.AMOUNTS, "HI-Small") is None
    assert source.is_connected() is False


@pytest.mark.integration
def test_data_source_reads_published_results(mongo_database):
    results = ResultsRepository(mongo_database)
    results.publish_variant(
        sample_summary("HI-Small"), [sample_result(AnalysisId.AMOUNTS, "HI-Small")]
    )
    source = AtlasDashboardDataSource(results, ExchangeRateRepository(mongo_database))
    assert source.is_connected() is True
    assert source.summary("HI-Small") == sample_summary("HI-Small")
    assert source.analysis(AnalysisId.AMOUNTS, "HI-Small").insight.startswith("Mediana")


def test_from_settings_does_not_need_a_reachable_database():
    settings = AmlSettings(_env_file=None, atlas_uri="mongodb://localhost:1", mongo_timeout_ms=300)
    source = AtlasDashboardDataSource.from_settings(settings)
    assert source.is_connected() is False and source.published_variants() == []
