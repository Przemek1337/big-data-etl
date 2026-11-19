from aml_etl.common.payment_formats import PaymentFormat


def test_payment_format_values():
    assert {p.value for p in PaymentFormat} == {
        "ACH",
        "Bitcoin",
        "Cash",
        "Cheque",
        "Credit Card",
        "Reinvestment",
        "Wire",
    }
