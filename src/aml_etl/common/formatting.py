COMPACT_UNITS = ((1e12, "bln"), (1e9, "mld"), (1e6, "mln"), (1e3, "tys."))


def _polish(text: str) -> str:
    return text.replace(",", " ").replace(".", ",")


def format_count(value: int) -> str:
    return _polish(f"{value:,}")


def format_usd(value: float) -> str:
    return "$" + _polish(f"{value:,.0f}")


def format_decimal(value: float, digits: int = 1) -> str:
    return _polish(f"{value:,.{digits}f}")


def format_percent(fraction: float, digits: int = 2) -> str:
    return f"{format_decimal(fraction * 100, digits)}%"


def _trimmed(value: float) -> str:
    return _polish(f"{value:,.2f}".rstrip("0").rstrip("."))


def format_compact(value: float) -> str:
    for threshold, unit in COMPACT_UNITS:
        if abs(value) >= threshold:
            return f"{_trimmed(value / threshold)} {unit}"
    return _trimmed(value)
