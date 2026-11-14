from aml_etl.common.logging import configure_logging
from aml_etl.common.settings import AmlSettings
from aml_etl.dashboard.app import create_app
from aml_etl.dashboard.data_source import AtlasDashboardDataSource

settings = AmlSettings()
configure_logging(settings.log_level)
create_app(AtlasDashboardDataSource.from_settings(settings)).run(
    host="0.0.0.0", port=8050, debug=False
)
