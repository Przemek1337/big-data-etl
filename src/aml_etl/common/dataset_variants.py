from dataclasses import dataclass

KNOWN_VARIANT_NAMES = frozenset(
    f"{risk}-{size}" for risk in ("HI", "LI") for size in ("Small", "Medium", "Large")
)


@dataclass(frozen=True)
class DatasetVariant:
    name: str

    def __post_init__(self) -> None:
        if self.name not in KNOWN_VARIANT_NAMES:
            known = ", ".join(sorted(KNOWN_VARIANT_NAMES))
            raise ValueError(f"Unknown dataset variant {self.name!r}; expected one of: {known}")

    @property
    def transactions_file_name(self) -> str:
        return f"{self.name}_Trans.csv"
