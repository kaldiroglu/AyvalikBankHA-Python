from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from ayvalikbank_ha.domain.model.rule_violation import AccountRuleViolation

from ayvalikbank_ha.domain.model import (
    AccountType,
    Currency,
    Money,
    SavingsAccount,
    TransactionType,
)


def test_opens_with_given_interest_rate():
    a = SavingsAccount.open(uuid4(), Currency.USD, Decimal("0.06"))
    assert a.type is AccountType.SAVINGS
    assert a.annual_interest_rate == Decimal("0.06")
    assert a.last_accrual_date is None


def test_negative_interest_rate_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        SavingsAccount.open(uuid4(), Currency.USD, Decimal("-0.01"))


def test_withdraw_cannot_go_negative():
    a = SavingsAccount.open(uuid4(), Currency.USD, Decimal("0.05"))
    a.deposit(Money(Decimal("50"), Currency.USD))
    with pytest.raises(AccountRuleViolation, match="Insufficient"):
        a.withdraw(Money(Decimal("60"), Currency.USD))


def test_accrue_interest_adds_monthly_interest():
    a = SavingsAccount.open(uuid4(), Currency.USD, Decimal("0.12"))
    a.deposit(Money(Decimal("1000"), Currency.USD))
    tx = a.accrue_interest(2026, 4)
    assert a.balance.amount == Decimal("1010.00")
    assert tx.type is TransactionType.INTEREST
    assert tx.amount.amount == Decimal("10.00")
    assert a.last_accrual_date == date(2026, 5, 1)


def test_accrue_interest_for_same_month_rejected():
    a = SavingsAccount.open(uuid4(), Currency.USD, Decimal("0.12"))
    a.deposit(Money(Decimal("1000"), Currency.USD))
    a.accrue_interest(2026, 4)
    with pytest.raises(AccountRuleViolation, match="already accrued"):
        a.accrue_interest(2026, 4)


def test_accrue_interest_on_closed_rejected():
    a = SavingsAccount.open(uuid4(), Currency.USD, Decimal("0.05"))
    a.close()
    with pytest.raises(AccountRuleViolation, match="closed"):
        a.accrue_interest(2026, 4)


def test_accrue_on_frozen_still_works():
    a = SavingsAccount.open(uuid4(), Currency.USD, Decimal("0.12"))
    a.deposit(Money(Decimal("1000"), Currency.USD))
    a.freeze()
    tx = a.accrue_interest(2026, 4)
    assert tx.amount.amount == Decimal("10.00")
