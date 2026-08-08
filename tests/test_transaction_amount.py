"""TransactionAmount is strictly positive; Money stays signed so overdraft keeps working.

Mirrors AyvalikBankHA-JAVA Refactorings.md entry 1 — with the weaker guarantee Python allows.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from ayvalikbank_ha.domain.model import Currency, Money, TransactionAmount


def test_accepts_a_positive_amount():
    a = TransactionAmount.of(100, Currency.USD)

    assert a.value.amount == Decimal("100")
    assert a.currency is Currency.USD


@pytest.mark.parametrize("amount", ["-50", "0"])
def test_rejects_non_positive_amounts(amount):
    with pytest.raises(ValueError, match="must be positive"):
        TransactionAmount.of(Decimal(amount), Currency.USD)


def test_money_itself_still_allows_negatives_so_overdraft_keeps_working():
    overdrawn = Money(Decimal("-500"), Currency.USD)

    assert overdrawn.amount == Decimal("-500")


def test_the_guarantee_is_a_convention_not_an_invariant():
    """Python cannot make an invalid value unconstructible.

    AyvalikBankHA-JAVA's record and AyvalikBankHA-NET's class both make this impossible.
    ``dataclasses.replace`` re-runs ``__post_init__`` so it is safe, but ``object.__new__``
    bypasses construction entirely. This test states the limitation rather than hiding it, so
    nobody reads the type as a guarantee it cannot give.
    """
    smuggled = object.__new__(TransactionAmount)
    object.__setattr__(smuggled, "value", Money(Decimal("-1"), Currency.USD))

    assert smuggled.value.amount == Decimal("-1")

    # the supported paths do validate
    with pytest.raises(ValueError):
        dataclasses.replace(TransactionAmount.of(5, Currency.USD), value=Money(Decimal("0"), Currency.USD))
