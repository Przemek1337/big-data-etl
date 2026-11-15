import logging
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from aml_etl.common.collections import LocalCollection
from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.common.exchange_rates import ExchangeRateRepository
from aml_etl.common.mongo import MongoDatabaseFactory
from aml_etl.common.settings import AmlSettings
from aml_etl.transactions_etl.csv_batch_reader import CsvBatchReader
from aml_etl.transactions_etl.data_quality_reporter import DataQualityReporter
from aml_etl.transactions_etl.import_progress import (
    ImportProgress,
    ImportProgressTracker,
    ImportStatus,
)
from aml_etl.transactions_etl.rate_table import RateTable
from aml_etl.transactions_etl.transaction_cleaner import TransactionCleaner
from aml_etl.transactions_etl.transaction_indexes import TransactionIndexManager
from aml_etl.transactions_etl.transaction_loader import TransactionLoader
from aml_etl.transactions_etl.usd_enricher import UsdEnricher

logger = logging.getLogger(__name__)

PROGRESS_EVERY_BATCHES = 10


class MissingRawFileError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


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
        tracker: ImportProgressTracker,
        quality_reporter: DataQualityReporter,
        clock: Callable[[], datetime],
    ) -> None:
        self._raw_dir = raw_dir
        self._variants = variants
        self._reader_factory = reader_factory
        self._cleaner_factory = cleaner_factory
        self._enricher = enricher
        self._loader = loader
        self._index_manager = index_manager
        self._tracker = tracker
        self._quality_reporter = quality_reporter
        self._clock = clock

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
        file_size = path.stat().st_size
        progress = self._starting_progress(variant, file_size)
        if progress.status is ImportStatus.COMPLETED:
            logger.info("%s already imported, skipping", variant.name)
            self._quality_reporter.publish(progress)
            return
        if progress.next_row_number:
            logger.info("%s resumes from row %d", variant.name, progress.next_row_number)
        else:
            logger.info("Importing %s", path.name)
        progress = self._import_batches(variant, path, progress)
        progress = progress.completed(self._clock())
        self._tracker.save(progress)
        self._quality_reporter.publish(progress)
        logger.info(
            "%s done: %d rows read, %d inserted, %d already present, %d rejected, "
            "%d exact duplicates kept",
            variant.name,
            progress.rows_read,
            progress.rows_inserted,
            progress.rows_already_present,
            progress.rows_rejected,
            progress.duplicate_rows,
        )

    def _starting_progress(self, variant: DatasetVariant, file_size: int) -> ImportProgress:
        saved = self._tracker.load(variant.name)
        if saved is None:
            return ImportProgress.start(variant.name, file_size, self._clock())
        if saved.source_file_size != file_size:
            logger.warning(
                "%s source file size changed from %d to %d bytes; importing again from row 0",
                variant.name,
                saved.source_file_size,
                file_size,
            )
            return ImportProgress.start(variant.name, file_size, self._clock())
        return saved

    def _import_batches(
        self, variant: DatasetVariant, path: Path, progress: ImportProgress
    ) -> ImportProgress:
        cleaner = self._cleaner_factory(variant)
        started = time.monotonic()
        first_row = progress.next_row_number
        batches = self._reader_factory(path).read_from(first_row)
        for batch_number, batch in enumerate(batches, start=1):
            cleaning = cleaner.transform(batch.frame)
            enrichment = self._enricher.transform(cleaning.frame)
            load = self._loader.load(enrichment.frame)
            progress = progress.after_batch(batch, cleaning, enrichment, load, self._clock())
            self._tracker.save(progress)
            if batch_number % PROGRESS_EVERY_BATCHES == 0:
                elapsed = max(time.monotonic() - started, 1e-9)
                logger.info(
                    "%s: row %d reached, %.0f rows/s",
                    variant.name,
                    progress.next_row_number,
                    (progress.next_row_number - first_row) / elapsed,
                )
        return progress


def build_import_job(settings: AmlSettings) -> TransactionImportJob:
    factory = MongoDatabaseFactory(settings)
    rate_table = RateTable(ExchangeRateRepository(factory.atlas()).find_all())
    local = factory.local()
    transactions = local[LocalCollection.TRANSACTIONS]
    return TransactionImportJob(
        raw_dir=settings.raw_dir,
        variants=settings.dataset_variants,
        reader_factory=lambda path: CsvBatchReader(path, settings.csv_batch_rows),
        cleaner_factory=TransactionCleaner,
        enricher=UsdEnricher(rate_table),
        loader=TransactionLoader(transactions),
        index_manager=TransactionIndexManager(transactions),
        tracker=ImportProgressTracker(local[LocalCollection.IMPORT_RUNS]),
        quality_reporter=DataQualityReporter(local[LocalCollection.DATA_QUALITY]),
        clock=utc_now,
    )
