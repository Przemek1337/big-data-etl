from enum import StrEnum


class PaymentFormat(StrEnum):
    ACH = "ACH"
    BITCOIN = "Bitcoin"
    CASH = "Cash"
    CHEQUE = "Cheque"
    CREDIT_CARD = "Credit Card"
    REINVESTMENT = "Reinvestment"
    WIRE = "Wire"
