"""A strictly positive monetary amount — the magnitude of a requested money movement."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .currency import Currency
from .money import Money


@dataclass(frozen=True, slots=True)
class TransactionAmount:
    """Wraps :class:`Money` and refuses anything that is not strictly positive.

    ``Money`` deliberately allows negatives — a checking account balance goes negative under
    overdraft — so it cannot enforce positivity, and every money-moving method re-asserted the rule
    by hand. Making the constraint a property of the *type* means it is checked once, at
    construction, and every method downstream can simply trust it.

    **Zero is rejected as well as negative.** Direction is already carried by which operation was
    called, so a signed amount is meaningless, and a zero-value transfer would write two ledger rows
    recording no movement of money.

    **Honest limitation.** In AyvalikBankHA-JAVA this makes an invalid amount genuinely
    unconstructible, and AyvalikBankHA-NET gets close by using a class rather than a struct (a C#
    struct always has ``default(T)``, which would bypass the constructor). Python offers no such
    guarantee: ``object.__new__`` and ``dataclasses.replace`` can both produce an instance without
    running ``__post_init__``. What this buys here is call-site clarity and a single place the rule
    lives — a strong convention, not an enforced invariant.

    Balances, transfer fees and recorded transaction amounts keep using ``Money``, because zero is
    legal for all three. Mirrors AyvalikBankHA-JAVA Refactorings.md entry 1.
    """

    value: Money

    def __post_init__(self) -> None:
        if self.value.amount <= 0:
            raise ValueError(f"Transaction amount must be positive, was {self.value.amount}")

    @staticmethod
    def of(amount: Decimal | int | float, currency: Currency) -> "TransactionAmount":
        return TransactionAmount(Money(Decimal(str(amount)), currency))

    @staticmethod
    def of_money(money: Money) -> "TransactionAmount":
        return TransactionAmount(money)

    @property
    def currency(self) -> Currency:
        return self.value.currency

    def __str__(self) -> str:
        return f"{self.value.amount} {self.value.currency}"
