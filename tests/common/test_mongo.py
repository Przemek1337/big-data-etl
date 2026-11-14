import pytest

from aml_etl.common.mongo import DatabaseUnavailableError, MongoDatabaseFactory, redact_uri
from aml_etl.common.settings import AmlSettings


def test_redact_uri_hides_credentials():
    assert redact_uri("mongodb+srv://u:secret@host.net/x?a=1") == "mongodb+srv://***@host.net/x?a=1"
    assert redact_uri("mongodb://localhost:27018") == "mongodb://localhost:27018"


@pytest.mark.integration
def test_factory_returns_configured_databases(aml_settings):
    factory = MongoDatabaseFactory(aml_settings)
    assert factory.local().name == aml_settings.local_database
    assert factory.atlas().name == aml_settings.atlas_database


@pytest.mark.integration
def test_unreachable_uri_raises_database_unavailable():
    settings = AmlSettings(
        _env_file=None, atlas_uri="mongodb://user:pw@localhost:1", mongo_timeout_ms=500
    )
    with pytest.raises(DatabaseUnavailableError) as error:
        MongoDatabaseFactory(settings).atlas()
    assert "pw" not in str(error.value) and "Atlas" in str(error.value)
