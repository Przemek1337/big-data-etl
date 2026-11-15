import logging
import time
from collections.abc import Callable

from aml_etl.common.etl import Job
from aml_etl.common.logging import configure_logging
from aml_etl.common.settings import AmlSettings


def run_service(
    service_name: str,
    build_job: Callable[[AmlSettings], Job],
    settings: AmlSettings | None = None,
) -> int:
    active_settings = settings if settings is not None else AmlSettings()
    configure_logging(active_settings.log_level)
    logger = logging.getLogger(service_name)
    started = time.monotonic()
    logger.info("%s started", service_name)
    try:
        build_job(active_settings).run()
    except Exception as error:
        logger.error(
            "%s failed: %s: %s",
            service_name,
            type(error).__name__,
            error,
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        return 1
    logger.info("%s finished in %.1fs", service_name, time.monotonic() - started)
    return 0
