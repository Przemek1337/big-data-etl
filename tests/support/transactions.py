import itertools
from datetime import UTC, datetime
from typing import Any

_row_numbers = itertools.count()


def reset_row_numbers() -> None:
    global _row_numbers
    _row_numbers = itertools.count()


def transaction_doc(**overrides: Any) -> dict[str, Any]:
    row_number = next(_row_numbers)
    document: dict[str, Any] = {
        "_id": f"HI-Small:{row_number}",
        "row_number": row_number,
        "dataset_variant": "HI-Small",
        "timestamp": datetime(2022, 9, 1, 10, 0, tzinfo=UTC),
        "from_bank": "001",
        "from_account": "A1",
        "to_bank": "002",
        "to_account": "B1",
        "amount_paid": 100.0,
        "amount_received": 100.0,
        "payment_currency": "USD",
        "receiving_currency": "USD",
        "payment_format": "ACH",
        "is_laundering": False,
        "amount_paid_usd": 100.0,
        "amount_received_usd": 100.0,
        "is_cross_currency": False,
    }
    document.update(overrides)
    if "dataset_variant" in overrides and "_id" not in overrides:
        document["_id"] = f"{overrides['dataset_variant']}:{row_number}"
    return document
