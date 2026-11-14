from aml_etl.common.service import run_service
from aml_etl.transactions_etl.import_job import build_import_job

raise SystemExit(run_service("transactions-etl", build_import_job))
