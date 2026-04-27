from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from ayvalikbank_ha.domain.model import (
    AccountType,
    Currency,
    Money,
    TimeDepositAccount,
    TransactionType,
)


def _new_one_year_usd(principal: Decimal = Decimal("10000"), rate: Decimal = Decimal("0.05")) -> TimeDepositAccount:
    maturity = (datetime.now(timezone.utc).date()).replace() + timedelta(days=365)
    return TimeDepositAccount.open(uuid4(), Currency.USD, Money(principal, Currency.USD), maturity, rate)


def test_opens_with_principal_as_balance():
    a = _new_one_year_usd(Decimal("5000"), Decimal("0.04"))
    assert a.type is AccountType.TIME_DEPOSIT
    assert a.balance.amount == Decimal("5000")
    assert a.principal.amount == Decimal("5000")
    assert a.matured is False


def test_deposit_rejected():
    a = _new_one_year_usd()
    with pytest.raises(PermissionError, match="locked"):
        a.deposit(Money(Decimal("100"), Currency.USD))


def test_transfer_out_rejected():
    a = _new_one_year_usd()
    with pytest.raises(PermissionError, match="do not support"):
        a.transfer_out(Money(Decimal("100"), Currency.USD), Money(Decimal("0"), Currency.USD), uuid4())


def test_withdraw_before_maturity_rejected():
    a = _new_one_year_usd()
    with pytest.raises(PermissionError, match="not matured"):
        a.withdraw(Money(Decimal("100"), Currency.USD))


def test_mature_before_maturity_date_rejected():
    a = _new_one_year_usd()
    today = datetime.now(timezone.utc).date()
    with pytest.raises(PermissionError, match="not yet reached"):
        a.mature(today)


def test_mature_credits_interest_and_allows_withdraw():
    a = _new_one_year_usd(Decimal("10000"), Decimal("0.05"))
    tx = a.mature(a.maturity_date)
    assert a.matured is True
    assert tx.type is TransactionType.INTEREST
    assert tx.amount.amount == Decimal("500.00")
    assert a.balance.amount == Decimal("10500.00")
    a.withdraw(Money(Decimal("2000"), Currency.USD))
    assert a.balance.amount == Decimal("8500.00")


def test_mature_twice_rejected():
    a = _new_one_year_usd()
    a.mature(a.maturity_date)
    with pytest.raises(PermissionError, match="already matured"):
        a.mature(a.maturity_date)


def test_non_positive_principal_rejected():
    maturity = datetime.now(timezone.utc).date() + timedelta(days=365)
    with pytest.raises(ValueError, match="positive"):
        TimeDepositAccount.open(uuid4(), Currency.USD, Money(Decimal("0"), Currency.USD), maturity, Decimal("0.05"))


def test_maturity_date_before_opened_on_rejected():
    today = datetime.now(timezone.utc).date()
    with pytest.raises(ValueError, match="Maturity date"):
        TimeDepositAccount.open(uuid4(), Currency.USD, Money(Decimal("100"), Currency.USD), today, Decimal("0.05"))
