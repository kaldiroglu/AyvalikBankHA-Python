from __future__ import annotations

from decimal import Decimal
from enum import Enum


class CustomerTier(str, Enum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    PRIVATE = "PRIVATE"

    def fee_multiplier(self) -> Decimal:
        return _FEE[self]

    def max_per_transfer(self) -> Decimal | None:
        return _TRANSFER_CAP[self]

    def max_per_withdrawal(self) -> Decimal | None:
        return _WITHDRAWAL_CAP[self]


_FEE: dict[CustomerTier, Decimal] = {
    CustomerTier.STANDARD: Decimal("1.00"),
    CustomerTier.PREMIUM: Decimal("0.50"),
    CustomerTier.PRIVATE: Decimal("0.00"),
}

_TRANSFER_CAP: dict[CustomerTier, Decimal | None] = {
    CustomerTier.STANDARD: Decimal("5000"),
    CustomerTier.PREMIUM: Decimal("50000"),
    CustomerTier.PRIVATE: None,
}

_WITHDRAWAL_CAP: dict[CustomerTier, Decimal | None] = {
    CustomerTier.STANDARD: Decimal("5000"),
    CustomerTier.PREMIUM: Decimal("25000"),
    CustomerTier.PRIVATE: None,
}
