from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import polars as pl

from aml_etl.common.dataset_variants import DatasetVariant

TIMESTAMP_COLUMN = "Timestamp"
TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M"


class MissingRawFileError(RuntimeError):
    pass


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def days(self) -> list[date]:
        count = (self.end - self.start).days + 1
        return [self.start + timedelta(days=offset) for offset in range(count)]


class TransactionDateRangeDetector:
    def __init__(self, raw_dir: Path) -> None:
        self._raw_dir = raw_dir

    def detect(self, variants: Sequence[DatasetVariant]) -> DateRange:
        bounds: list[date] = []
        for variant in variants:
            path = self._raw_dir / variant.transactions_file_name
            if not path.exists():
                message = f"Raw file {path.name} not found in {self._raw_dir}"
                raise MissingRawFileError(f"{message}; run dataset-extractor first")
            bounds.extend(self._file_bounds(path))
        return DateRange(min(bounds), max(bounds))

    def _file_bounds(self, path: Path) -> list[date]:
        timestamps = pl.scan_csv(path, infer_schema=False).select(
            pl.col(TIMESTAMP_COLUMN).str.to_datetime(TIMESTAMP_FORMAT, strict=False)
        )
        row = timestamps.select(
            pl.col(TIMESTAMP_COLUMN).min().alias("first"),
            pl.col(TIMESTAMP_COLUMN).max().alias("last"),
        ).collect()
        values = [row["first"][0], row["last"][0]]
        if not all(isinstance(value, datetime) for value in values):
            raise MissingRawFileError(f"Raw file {path.name} has no readable timestamps")
        return [value.date() for value in values]
