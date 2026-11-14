from aml_etl.common.service import run_service
from aml_etl.rates_scraper.scraping_job import build_scraping_job

raise SystemExit(run_service("rates-scraper", build_scraping_job))
