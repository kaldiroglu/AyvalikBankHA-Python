from decimal import Decimal
from uuid import uuid4

import pytest

from ayvalikbank_ha.domain.model.rule_violation import AccountRuleViolation

from ayvalikbank_ha.domain.model import (
    AccountStatus,
    AccountType,
    CheckingAccount,
    Currency,
    Money,
)


def test_opens_without_overdraft_by_default():
    a = CheckingAccount.open(uuid4(), Currency.USD)
    assert a.type is AccountType.CHECKING
    assert a.overdraft_limit.amount == Decimal("0")


def test_opens_with_overdraft_limit():
    a = CheckingAccount.open(uuid4(), Currency.USD, Money(Decimal("500"), Currency.USD))
    assert a.overdraft_limit.amount == Decimal("500")


def test_withdraw_without_overdraft_rejects_overdraw():
    a = CheckingAccount.open(uuid4(), Currency.USD)
    a.deposit(Money(Decimal("50"), Currency.USD))
    with pytest.raises(AccountRuleViolation, match="Insufficient"):
        a.withdraw(Money(Decimal("100"), Currency.USD))


def test_withdraw_within_overdraft_allows_negative_balance():
    a = CheckingAccount.open(uuid4(), Currency.USD, Money(Decimal("200"), Currency.USD))
    a.deposit(Money(Decimal("50"), Currency.USD))
    a.withdraw(Money(Decimal("150"), Currency.USD))
    assert a.balance.amount == Decimal("-100")


def test_withdraw_beyond_overdraft_throws():
    a = CheckingAccount.open(uuid4(), Currency.USD, Money(Decimal("100"), Currency.USD))
    with pytest.raises(AccountRuleViolation, match="overdraft"):
        a.withdraw(Money(Decimal("101"), Currency.USD))


def test_overdraft_currency_must_match():
    with pytest.raises(ValueError, match="currency"):
        CheckingAccount(
            uuid4(),
            uuid4(),
            Currency.USD,
            Money.zero(Currency.USD),
            AccountStatus.ACTIVE,
            Money(Decimal("100"), Currency.EUR),
        )


def test_negative_overdraft_rejected():
    with pytest.raises(ValueError, match="negative"):
        CheckingAccount(
            uuid4(),
            uuid4(),
            Currency.USD,
            Money.zero(Currency.USD),
            AccountStatus.ACTIVE,
            Money(Decimal("-1"), Currency.USD),
        )
