from enum import Enum


class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    TIME_DEPOSIT = "TIME_DEPOSIT"
