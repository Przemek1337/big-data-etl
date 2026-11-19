import pytest

from aml_etl.analytics.statistics import chi_square_test, odds_ratio


def test_chi_square_ignores_empty_rows_and_needs_two_by_two():
    assert chi_square_test([[10, 0], [0, 0]], "x") is None
    result = chi_square_test([[30, 10], [10, 30], [0, 0]], "x")
    assert result.p_value < 0.001
    assert result.name == "Chi-kwadrat niezależności" and result.sample_description == "x"


def test_odds_ratio():
    assert odds_ratio([[90, 10], [60, 40]]) == pytest.approx(6.0)


def test_odds_ratio_with_zero_cell_is_undefined():
    assert odds_ratio([[90, 0], [60, 40]]) is None
