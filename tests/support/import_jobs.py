from datetime import date
from pathlib import Path
from typing import Any

import polars as pl
from pymongo.database import Database
from support.clean_frames import clean_frame, eur, row, usd
from support.results import NOW

from aml_etl.common.collections import LocalCollection
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.settings import AmlSettings
from aml_etl.transactions_etl.csv_batch_reader import CsvBatchReader
from aml_etl.transactions_etl.data_quality_reporter import DataQualityReporter
from aml_etl.transactions_etl.import_job import TransactionImportJob
from aml_etl.transactions_etl.import_progress import ImportProgress, ImportProgressTracker
from aml_etl.transactions_etl.rate_table import RateTable
from aml_etl.transactions_etl.transaction_cleaner import TransactionCleaner
from aml_etl.transactions_etl.transaction_indexes import TransactionIndexManager
from aml_etl.transactions_etl.transaction_loader import LoadResult, TransactionLoader
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


def make_raw_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    return raw_dir


def production_settings(tmp_path: Path, settings: AmlSettings, batch_rows: int) -> AmlSettings:
    make_raw_dir(tmp_path)
    return settings.model_copy(
        update={
            "data_dir": tmp_path,
            "csv_batch_rows": batch_rows,
            "dataset_variants": [DatasetVariant("HI-Small")],
        }
    )


class FailingLoader:
    def __init__(self, inner: TransactionLoader, fails_on_call: int) -> None:
        self._inner = inner
        self._fails_on_call = fails_on_call
        self._calls = 0

    def load(self, item: pl.DataFrame) -> LoadResult:
        self._calls += 1
        if self._calls == self._fails_on_call:
            raise RuntimeError("loader crashed")
        return self._inner.load(item)


class FailingTracker:
    def __init__(self, inner: ImportProgressTracker, fails_on_save: int) -> None:
        self._inner = inner
        self._fails_on_save = fails_on_save
        self._saves = 0

    def load(self, variant: str) -> ImportProgress | None:
        return self._inner.load(variant)

    def save(self, progress: ImportProgress) -> None:
        self._saves += 1
        if self._saves == self._fails_on_save:
            raise RuntimeError("tracker crashed")
        self._inner.save(progress)


def build_test_job(
    tmp_path: Path,
    settings: AmlSettings,
    batch_rows: int,
    loader_fails_on_call: int | None = None,
    tracker_fails_on_save: int | None = None,
) -> TransactionImportJob:
    seed_rates(settings)
    local = local_db(settings)
    transactions = local[LocalCollection.TRANSACTIONS]
    loader: Any = TransactionLoader(transactions)
    if loader_fails_on_call is not None:
        loader = FailingLoader(loader, loader_fails_on_call)
    tracker: Any = ImportProgressTracker(local[LocalCollection.IMPORT_RUNS])
    if tracker_fails_on_save is not None:
        tracker = FailingTracker(tracker, tracker_fails_on_save)
    rates = ExchangeRateRepository(atlas_db(settings)).find_all()
    return TransactionImportJob(
        raw_dir=make_raw_dir(tmp_path),
        variants=[DatasetVariant("HI-Small")],
        reader_factory=lambda path: CsvBatchReader(path, batch_rows),
        cleaner_factory=TransactionCleaner,
        enricher=UsdEnricher(RateTable(rates)),
        loader=loader,
        index_manager=TransactionIndexManager(transactions),
        tracker=tracker,
        quality_reporter=DataQualityReporter(local[LocalCollection.DATA_QUALITY]),
        clock=lambda: NOW,
    )
