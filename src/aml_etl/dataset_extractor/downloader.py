from pathlib import Path
from typing import Protocol

import kagglehub


class DatasetFileDownloader(Protocol):
    def download(self, file_name: str, target_dir: Path) -> Path: ...


class KaggleDatasetFileDownloader:
    def __init__(self, dataset_handle: str) -> None:
        self._dataset_handle = dataset_handle

    def download(self, file_name: str, target_dir: Path) -> Path:
        downloaded = kagglehub.dataset_download(
            self._dataset_handle, path=file_name, output_dir=str(target_dir)
        )
        return Path(downloaded)
