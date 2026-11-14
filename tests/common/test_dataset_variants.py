import pytest

from aml_etl.common.dataset_variants import DatasetVariant


def test_transactions_file_name():
    assert DatasetVariant("LI-Medium").transactions_file_name == "LI-Medium_Trans.csv"


def test_unknown_variant_rejected():
    with pytest.raises(ValueError):
        DatasetVariant("XX-Small")
