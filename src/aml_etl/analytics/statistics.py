import numpy as np
from scipy import stats

from aml_etl.common.results import StatisticalTest

CHI_SQUARE_NAME = "Chi-kwadrat niezależności"
MINIMUM_DIMENSION = 2


def chi_square_test(table: list[list[int]], sample_description: str) -> StatisticalTest | None:
    observed = np.array(table, dtype=np.int64)
    if observed.ndim != MINIMUM_DIMENSION:
        return None
    observed = observed[observed.sum(axis=1) > 0][:, observed.sum(axis=0) > 0]
    if observed.shape[0] < MINIMUM_DIMENSION or observed.shape[1] < MINIMUM_DIMENSION:
        return None
    result = stats.chi2_contingency(observed)
    return StatisticalTest(
        name=CHI_SQUARE_NAME,
        statistic=float(result.statistic),
        p_value=float(result.pvalue),
        sample_description=sample_description,
    )


def odds_ratio(table_2x2: list[list[int]]) -> float | None:
    (a, b), (c, d) = table_2x2
    if b == 0 or c == 0:
        return None
    return (a * d) / (b * c)
