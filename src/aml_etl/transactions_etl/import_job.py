import logging
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from aml_etl.common.collections import LocalCollection
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.settings import AmlSettings
from aml_etl.transactions_etl.csv_batch_reader import CsvBatchReader
from aml_etl.transactions_etl.rate_table import RateTable
from aml_etl.transactions_etl.transaction_cleaner import TransactionCleaner
from aml_etl.transactions_etl.transaction_indexes import TransactionIndexManager
from aml_etl.transactions_etl.transaction_loader import TransactionLoader
from aml_etl.transactions_etl.usd_enricher import UsdEnricher

logger = logging.getLogger(__name__)

PROGRESS_EVERY_BATCHES = 10


class MissingRawFileError(RuntimeError):
    pass


class TransactionImportJob:
    def __init__(
        self,
        raw_dir: Path,
        variants: Sequence[DatasetVariant],
        reader_factory: Callable[[Path], CsvBatchReader],
        cleaner_factory: Callable[[DatasetVariant], TransactionCleaner],
        enricher: UsdEnricher,
        loader: TransactionLoader,
        index_manager: TransactionIndexManager,
    ) -> None:
        self._raw_dir = raw_dir
        self._variants = variants
        self._reader_factory = reader_factory
        self._cleaner_factory = cleaner_factory
        self._enricher = enricher
        self._loader = loader
        self._index_manager = index_manager

    def run(self) -> None:
        for variant in self._variants:
            self._import_variant(variant)
        self._index_manager.ensure_indexes()

    def _import_variant(self, variant: DatasetVariant) -> None:
        path = self._raw_dir / variant.transactions_file_name
        if not path.exists():
            raise MissingRawFileError(
                f"Raw file {path.name} not found in {self._raw_dir}; run dataset-extractor first"
            )
        cleaner = self._cleaner_factory(variant)
        started = time.monotonic()
        rows_read = inserted = already_present = 0
        logger.info("Importing %s", path.name)
        for batch_number, batch in enumerate(self._reader_factory(path).read_from(0), start=1):
            cleaned = cleaner.transform(batch.frame)
            result = self._loader.load(self._enricher.transform(cleaned.frame).frame)
            rows_read = batch.next_row_number
            inserted += result.inserted
            already_present += result.already_present
            if batch_number % PROGRESS_EVERY_BATCHES == 0:
                elapsed = max(time.monotonic() - started, 1e-9)
                logger.info(
                    "%s: %d rows read, %.0f rows/s", variant.name, rows_read, rows_read / elapsed
                )
        logger.info(
            "%s done: %d rows read, %d inserted, %d already present, %.1fs",
            variant.name,
            rows_read,
            inserted,
            already_present,
            time.monotonic() - started,
        )


def build_import_job(settings: AmlSettings) -> TransactionImportJob:
    factory = MongoDatabaseFactory(settings)
    rate_table = RateTable(ExchangeRateRepository(factory.atlas()).find_all())
    transactions = factory.local()[LocalCollection.TRANSACTIONS]
    return TransactionImportJob(
        raw_dir=settings.raw_dir,
        variants=settings.dataset_variants,
        reader_factory=lambda path: CsvBatchReader(path, settings.csv_batch_rows),
        cleaner_factory=TransactionCleaner,
        enricher=UsdEnricher(rate_table),
        loader=TransactionLoader(transactions),
        index_manager=TransactionIndexManager(transactions),
    )
