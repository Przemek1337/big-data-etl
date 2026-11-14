from datetime import date
from pathlib import Path
from typing import Any

import polars as pl
from pymongo.database import Database
from support.clean_frames import clean_frame, eur, row, usd

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.settings import AmlSettings
from aml_etl.transactions_etl.import_job import TransactionImportJob, build_import_job
from aml_etl.transactions_etl.rate_table import RateTable
from aml_etl.transactions_etl.usd_enricher import UsdEnricher

RATE_DAY = date(2022, 9, 1)


def enriched_frame(count: int) -> pl.DataFrame:
    enricher = UsdEnricher(RateTable([usd(RATE_DAY)]))
    return enricher.transform(clean_frame(*[row() for _ in range(count)])).frame


def local_db(settings: AmlSettings) -> Database[dict[str, Any]]:
    return MongoDatabaseFactory(settings).local()


def atlas_db(settings: AmlSettings) -> Database[dict[str, Any]]:
    return MongoDatabaseFactory(settings).atlas()


def seed_rates(settings: AmlSettings) -> None:
    ExchangeRateRepository(atlas_db(settings)).upsert_many([usd(RATE_DAY), eur(RATE_DAY, 1.0039)])


def job_settings(raw_dir: Path, settings: AmlSettings, batch_rows: int) -> AmlSettings:
    return settings.model_copy(
        update={
            "data_dir": raw_dir.parent,
            "csv_batch_rows": batch_rows,
            "dataset_variants": [DatasetVariant("HI-Small")],
        }
    )


def make_raw_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    return raw_dir


def build_test_job(tmp_path: Path, settings: AmlSettings, batch_rows: int) -> TransactionImportJob:
    seed_rates(settings)
    return build_import_job(job_settings(make_raw_dir(tmp_path), settings, batch_rows))
