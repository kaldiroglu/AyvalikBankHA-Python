from decimal import Decimal

import pytest

from ayvalikbank_ha.domain.model import Currency, Money


def test_zero_is_zero():
    m = Money.zero(Currency.USD)
    assert m.amount == Decimal("0")
    assert m.currency is Currency.USD


def test_adds_same_currency():
    a = Money(Decimal("100"), Currency.USD)
    b = Money(Decimal("50"), Currency.USD)
    assert a.add(b).amount == Decimal("150")


def test_rejects_add_different_currency():
    a = Money(Decimal("100"), Currency.USD)
    b = Money(Decimal("50"), Currency.EUR)
    with pytest.raises(ValueError, match="match"):
        a.add(b)


def test_gte_works_within_same_currency():
    a = Money(Decimal("100"), Currency.USD)
    b = Money(Decimal("50"), Currency.USD)
    assert a.is_greater_than_or_equal_to(b)
    assert not b.is_greater_than_or_equal_to(a)
