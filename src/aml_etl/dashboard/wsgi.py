from aml_etl.common.logging import configure_logging
from aml_etl.common.settings import AmlSettings
from aml_etl.dashboard.app import create_app
from aml_etl.dashboard.data_source import AtlasDashboardDataSource

settings = AmlSettings()
configure_logging(settings.log_level)
server = create_app(AtlasDashboardDataSource.from_settings(settings)).server
