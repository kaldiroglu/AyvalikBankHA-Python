from enum import Enum


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    TRY = "TRY"
    GBP = "GBP"
