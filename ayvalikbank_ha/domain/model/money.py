from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .currency import Currency


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    @staticmethod
    def zero(currency: Currency) -> "Money":
        return Money(Decimal("0"), currency)

    def add(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def is_greater_than_or_equal_to(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount >= other.amount

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Currency {other.currency} does not match {self.currency}"
            )
