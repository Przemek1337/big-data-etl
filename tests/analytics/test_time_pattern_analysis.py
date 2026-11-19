from datetime import UTC, datetime

import pytest
from support.results import NOW
from support.transactions import transaction_doc

from aml_etl.analytics.time_pattern_analysis import TimePatternAnalysis
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.results import AnalysisId

VARIANT = DatasetVariant("HI-Small")


def at_hour(hour: int, day: int = 1) -> datetime:
    return datetime(2022, 9, day, hour, 0, tzinfo=UTC)


@pytest.mark.integration
def test_time_pattern_analysis(seed):
    docs = [
        transaction_doc(timestamp=at_hour(14), is_laundering=True),
        transaction_doc(timestamp=at_hour(14)),
        transaction_doc(timestamp=at_hour(3)),
        transaction_doc(timestamp=at_hour(3)),
    ]
    result = TimePatternAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert result.analysis_id is AnalysisId.TIME_PATTERNS
    assert len(result.tables["by_hour"]) == 24 and len(result.tables["by_weekday"]) == 7
    assert [row["hour"] for row in result.tables["by_hour"]] == list(range(24))
    assert result.tables["by_hour"][14] == {
        "hour": 14,
        "transaction_count": 2,
        "laundering_count": 1,
        "laundering_rate": 0.5,
    }
    assert result.tables["by_hour"][0]["transaction_count"] == 0
    assert (
        result.insight
        == "Najwyższy odsetek prania przypada na godzinę 14:00–15:00: 50,00% transakcji."
    )
    assert result.statistical_test is not None


@pytest.mark.integration
def test_weekday_table_uses_polish_labels(seed):
    docs = [transaction_doc(timestamp=at_hour(10, day=4), is_laundering=True), transaction_doc()]
    result = TimePatternAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    labels = [row["weekday_label"] for row in result.tables["by_weekday"]]
    assert labels == ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
    sunday = result.tables["by_weekday"][6]
    assert (sunday["weekday"], sunday["transaction_count"], sunday["laundering_count"]) == (7, 1, 1)
    assert result.tables["by_weekday"][3]["transaction_count"] == 1


@pytest.mark.integration
def test_last_hour_of_day_ends_at_midnight(seed):
    docs = [transaction_doc(timestamp=at_hour(23), is_laundering=True), transaction_doc()]
    result = TimePatternAnalysis(lambda: NOW).compute(seed(docs), VARIANT)
    assert "godzinę 23:00–00:00" in result.insight
