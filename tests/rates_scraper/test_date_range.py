from datetime import date

import pytest
from support.csv_rows import write_csv

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.rates_scraper.date_range import (
    DateRange,
    MissingRawFileError,
    TransactionDateRangeDetector,
)


def test_days_are_inclusive():
    assert DateRange(date(2022, 8, 31), date(2022, 9, 2)).days() == [
        date(2022, 8, 31),
        date(2022, 9, 1),
        date(2022, 9, 2),
    ]


def test_detects_range_across_files(tmp_path):
    write_csv(tmp_path / "HI-Small_Trans.csv", ["2022/09/01 00:20", "2022/09/05 10:00"])
    write_csv(tmp_path / "LI-Small_Trans.csv", ["2022/09/03 00:00", "2022/09/18 23:59"])
    rng = TransactionDateRangeDetector(tmp_path).detect(
        [DatasetVariant("HI-Small"), DatasetVariant("LI-Small")]
    )
    assert rng == DateRange(date(2022, 9, 1), date(2022, 9, 18))


def test_missing_raw_file_raises_with_file_name(tmp_path):
    with pytest.raises(MissingRawFileError, match="HI-Small_Trans"):
        TransactionDateRangeDetector(tmp_path).detect([DatasetVariant("HI-Small")])
