import logging
import shutil
from collections.abc import Iterator, Sequence
from pathlib import Path

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.dataset_extractor.archive_unpacker import unpack_if_archive
from aml_etl.dataset_extractor.downloader import DatasetFileDownloader

logger = logging.getLogger(__name__)

PARTIAL_DIR_NAME = ".partial"


class RawDatasetExtractor:
    def __init__(
        self,
        downloader: DatasetFileDownloader,
        raw_dir: Path,
        variants: Sequence[DatasetVariant],
    ) -> None:
        self._downloader = downloader
        self._raw_dir = raw_dir
        self._variants = variants

    def extract(self) -> Iterator[Path]:
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        for variant in self._variants:
            yield self._extract_file(variant.transactions_file_name)

    def _extract_file(self, file_name: str) -> Path:
        target = self._raw_dir / file_name
        marker = self._raw_dir / f"{file_name}.complete"
        if marker.exists() and target.exists():
            logger.info("%s already extracted, skipping download", file_name)
            return target
        partial_dir = self._raw_dir / PARTIAL_DIR_NAME
        shutil.rmtree(partial_dir, ignore_errors=True)
        partial_dir.mkdir(parents=True)
        logger.info("Downloading %s", file_name)
        downloaded = self._downloader.download(file_name, partial_dir)
        unpack_if_archive(downloaded, partial_dir).replace(target)
        shutil.rmtree(partial_dir, ignore_errors=True)
        marker.touch()
        return target
