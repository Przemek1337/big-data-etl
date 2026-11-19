import polars as pl
from support.csv_rows import VALID

from aml_etl.transactions_etl.transaction_schema import RAW_COLUMNS, ROW_NUMBER_COLUMN


def raw_row(**overrides: str) -> dict[str, str]:
    values = dict(zip(RAW_COLUMNS, VALID.split(","), strict=True))
    values.update(overrides)
    return values


def raw_frame(*rows: dict[str, str]) -> pl.DataFrame:
    frame = pl.DataFrame(list(rows), schema=dict.fromkeys(RAW_COLUMNS, pl.Utf8))
    return frame.with_columns(pl.Series(ROW_NUMBER_COLUMN, list(range(len(rows))), dtype=pl.Int64))
