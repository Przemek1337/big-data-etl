from aml_etl.common.service import run_service
from aml_etl.dataset_extractor.extraction_job import build_extraction_job

raise SystemExit(run_service("dataset-extractor", build_extraction_job))
