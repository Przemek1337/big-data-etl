from aml_etl.analytics.analytics_job import build_analytics_job
from aml_etl.common.service import run_service

raise SystemExit(run_service("analytics", build_analytics_job))
