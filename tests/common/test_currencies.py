import pytest

from aml_etl.common.currencies import Currency, UnknownCurrencyError


def test_every_dataset_currency_name_is_mapped():
    assert {c.dataset_name for c in Currency} == {
        "US Dollar",
        "Euro",
        "Yuan",
        "Yen",
        "Rupee",
        "Ruble",
        "Swiss Franc",
        "Bitcoin",
        "Brazil Real",
        "Australian Dollar",
        "Canadian Dollar",
        "Mexican Peso",
        "Saudi Riyal",
        "UK Pound",
        "Shekel",
    }


def test_from_dataset_name():
    assert Currency.from_dataset_name("UK Pound") is Currency.GBP
    assert Currency.from_dataset_name("Rupee") is Currency.INR


def test_x_rates_names_cover_all_fiat_except_usd():
    assert {c for c in Currency if c.x_rates_name} == set(Currency) - {Currency.USD, Currency.BTC}
    assert Currency.from_x_rates_name("Saudi Arabian Riyal") is Currency.SAR


def test_unknown_currency_raises():
    with pytest.raises(UnknownCurrencyError):
        Currency.from_dataset_name("Zloty")
    with pytest.raises(UnknownCurrencyError):
        Currency.from_x_rates_name("Polish Zloty")
