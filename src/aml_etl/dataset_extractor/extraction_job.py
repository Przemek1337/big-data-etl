import logging
from pathlib import Path

from aml_etl.common.etl import Extractor
from aml_etl.common.settings import AmlSettings
from aml_etl.dataset_extractor.downloader import KaggleDatasetFileDownloader
from aml_etl.dataset_extractor.raw_dataset_extractor import RawDatasetExtractor

logger = logging.getLogger(__name__)

BYTES_PER_GB = 1024**3


class ExtractionJob:
    def __init__(
        self, extractor: Extractor[Path], minimum_total_bytes: int = 5 * BYTES_PER_GB
    ) -> None:
        self._extractor = extractor
        self._minimum_total_bytes = minimum_total_bytes

    def run(self) -> None:
        total_bytes = 0
        for path in self._extractor.extract():
            size = path.stat().st_size
            total_bytes += size
            logger.info("%s ready: %.2f GB", path.name, size / BYTES_PER_GB)
        if total_bytes < self._minimum_total_bytes:
            logger.warning(
                "Raw data totals %.2f GB, below the 5 GB course threshold",
                total_bytes / BYTES_PER_GB,
            )


def build_extraction_job(settings: AmlSettings) -> ExtractionJob:
    downloader = KaggleDatasetFileDownloader(settings.kaggle_dataset)
    extractor = RawDatasetExtractor(downloader, settings.raw_dir, settings.dataset_variants)
    return ExtractionJob(extractor)
