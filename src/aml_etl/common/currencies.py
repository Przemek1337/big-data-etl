from enum import StrEnum
from typing import Self


class UnknownCurrencyError(ValueError):
    pass


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"
    JPY = "JPY"
    INR = "INR"
    RUB = "RUB"
    CHF = "CHF"
    BTC = "BTC"
    BRL = "BRL"
    AUD = "AUD"
    CAD = "CAD"
    MXN = "MXN"
    SAR = "SAR"
    GBP = "GBP"
    ILS = "ILS"

    @property
    def dataset_name(self) -> str:
        return _NAMES[self.value][0]

    @property
    def x_rates_name(self) -> str | None:
        return _NAMES[self.value][1]

    @classmethod
    def from_dataset_name(cls, name: str) -> Self:
        for currency in cls:
            if currency.dataset_name == name:
                return currency
        raise UnknownCurrencyError(f"Unknown dataset currency name: {name!r}")

    @classmethod
    def from_x_rates_name(cls, name: str) -> Self:
        for currency in cls:
            if currency.x_rates_name == name:
                return currency
        raise UnknownCurrencyError(f"Unknown x-rates currency name: {name!r}")


_NAMES: dict[str, tuple[str, str | None]] = {
    "USD": ("US Dollar", None),
    "EUR": ("Euro", "Euro"),
    "CNY": ("Yuan", "Chinese Yuan Renminbi"),
    "JPY": ("Yen", "Japanese Yen"),
    "INR": ("Rupee", "Indian Rupee"),
    "RUB": ("Ruble", "Russian Ruble"),
    "CHF": ("Swiss Franc", "Swiss Franc"),
    "BTC": ("Bitcoin", None),
    "BRL": ("Brazil Real", "Brazilian Real"),
    "AUD": ("Australian Dollar", "Australian Dollar"),
    "CAD": ("Canadian Dollar", "Canadian Dollar"),
    "MXN": ("Mexican Peso", "Mexican Peso"),
    "SAR": ("Saudi Riyal", "Saudi Arabian Riyal"),
    "GBP": ("UK Pound", "British Pound"),
    "ILS": ("Shekel", "Israeli Shekel"),
}
