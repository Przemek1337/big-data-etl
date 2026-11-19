from pathlib import Path

from aml_etl.transactions_etl.transaction_schema import EXPECTED_HEADER, RAW_COLUMNS

VALID = (
    "2022/09/01 00:20,010,8000EBD30,010,8000EBD30,3697.34,US Dollar,3697.34,US Dollar,"
    "Reinvestment,0"
)


def valid_row(**overrides: str) -> str:
    values = dict(zip(RAW_COLUMNS, VALID.split(","), strict=True))
    unknown = set(overrides) - set(RAW_COLUMNS)
    if unknown:
        raise KeyError(f"Unknown columns: {sorted(unknown)}")
    values.update(overrides)
    return ",".join(values[column] for column in RAW_COLUMNS)


def write_rows(path: Path, rows: list[str]) -> Path:
    path.write_text("\n".join([EXPECTED_HEADER, *rows]) + "\n", encoding="utf-8", newline="")
    return path


def write_csv(path: Path, timestamps: list[str]) -> Path:
    return write_rows(path, [valid_row(timestamp=timestamp) for timestamp in timestamps])
