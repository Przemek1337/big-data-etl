from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import polars as pl

from aml_etl.transactions_etl.transaction_schema import (
    EXPECTED_HEADER,
    RAW_COLUMNS,
    ROW_NUMBER_COLUMN,
    UnexpectedHeaderError,
)

LINE_ENDINGS = b"\r\n"
EXPECTED_SEPARATORS = len(RAW_COLUMNS) - 1


@dataclass(frozen=True)
class CsvBatch:
    first_row_number: int
    next_row_number: int
    frame: pl.DataFrame
    malformed_line_count: int


class CsvBatchReader:
    def __init__(self, path: Path, batch_rows: int) -> None:
        self._path = path
        self._batch_rows = batch_rows

    def extract(self) -> Iterator[CsvBatch]:
        return self.read_from(0)

    def read_from(self, row_number: int = 0) -> Iterator[CsvBatch]:
        with self._path.open("rb") as source:
            self._validate_header(source.readline())
            current = 0
            while current < row_number and source.readline():
                current += 1
            while True:
                batch = self._read_batch(source, current)
                if batch is None:
                    return
                current = batch.next_row_number
                yield batch

    def _validate_header(self, line: bytes) -> None:
        header = line.rstrip(LINE_ENDINGS).decode("utf-8", errors="replace")
        if header != EXPECTED_HEADER:
            raise UnexpectedHeaderError(f"Unexpected header in {self._path.name}: {header[:200]!r}")

    def _read_batch(self, source: BinaryIO, first: int) -> CsvBatch | None:
        current = first
        numbers: list[int] = []
        lines: list[bytes] = []
        malformed = 0
        while current - first < self._batch_rows:
            line = source.readline()
            if not line:
                break
            number = current
            current += 1
            stripped = line.rstrip(LINE_ENDINGS)
            if not stripped:
                continue
            if stripped.count(b",") != EXPECTED_SEPARATORS:
                malformed += 1
                continue
            numbers.append(number)
            lines.append(stripped)
        if current == first:
            return None
        frame = self._frame(lines).with_columns(
            pl.Series(ROW_NUMBER_COLUMN, numbers, dtype=pl.Int64)
        )
        return CsvBatch(first, current, frame, malformed)

    def _frame(self, lines: list[bytes]) -> pl.DataFrame:
        if not lines:
            return pl.DataFrame(schema=dict.fromkeys(RAW_COLUMNS, pl.Utf8))
        return pl.read_csv(
            BytesIO(b"\n".join(lines)),
            has_header=False,
            new_columns=list(RAW_COLUMNS),
            infer_schema=False,
            quote_char=None,
            encoding="utf8-lossy",
        )
