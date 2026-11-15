from pathlib import Path

import pytest
from pydantic import ValidationError

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.settings import AmlSettings


def test_settings_defaults(monkeypatch):
    for key in ("DATASET_VARIANTS", "ATLAS_DATABASE", "ATLAS_URI", "LOG_LEVEL", "LOCAL_MONGO_URI"):
        monkeypatch.delenv(key, raising=False)
    settings = AmlSettings(_env_file=None)
    assert settings.dataset_variants == [DatasetVariant("HI-Medium"), DatasetVariant("LI-Medium")]
    assert settings.atlas_database == "aml_results" and settings.local_database == "aml"
    assert settings.local_mongo_uri == settings.atlas_uri == "mongodb://localhost:27018"
    assert settings.raw_dir == Path("data") / "raw"


def test_dataset_variants_from_comma_separated_env(monkeypatch):
    monkeypatch.setenv("DATASET_VARIANTS", "HI-Small, LI-Medium")
    assert AmlSettings(_env_file=None).dataset_variants == [
        DatasetVariant("HI-Small"),
        DatasetVariant("LI-Medium"),
    ]


def test_unknown_variant_in_env_is_validation_error(monkeypatch):
    monkeypatch.setenv("DATASET_VARIANTS", "HI-Huge")
    with pytest.raises(ValidationError):
        AmlSettings(_env_file=None)


def test_log_level_is_normalised_and_validated(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert AmlSettings(_env_file=None).log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "verbose")
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        AmlSettings(_env_file=None)


def test_empty_variant_list_is_rejected(monkeypatch):
    monkeypatch.setenv("DATASET_VARIANTS", " , ")
    with pytest.raises(ValidationError, match="DATASET_VARIANTS"):
        AmlSettings(_env_file=None)


def test_batch_size_must_be_positive(monkeypatch):
    monkeypatch.setenv("CSV_BATCH_ROWS", "0")
    with pytest.raises(ValidationError):
        AmlSettings(_env_file=None)
