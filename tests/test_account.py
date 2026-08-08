from decimal import Decimal
from uuid import uuid4

import pytest

from ayvalikbank_ha.domain.model import TransactionAmount

from ayvalikbank_ha.domain.model.rule_violation import AccountRuleViolation

from ayvalikbank_ha.domain.model import (
    AccountStatus,
    CheckingAccount,
    Currency,
    Money,
    TransactionType,
)


def _new_usd() -> CheckingAccount:
    return CheckingAccount.open(uuid4(), Currency.USD)


def test_opens_at_zero_and_active():
    a = _new_usd()
    assert a.balance.amount == Decimal("0")
    assert a.status is AccountStatus.ACTIVE


def test_deposit_raises_balance_and_returns_transaction():
    a = _new_usd()
    tx = a.deposit(TransactionAmount.of_money(Money(Decimal("500"), Currency.USD)))
    assert a.balance.amount == Decimal("500")
    assert tx.type is TransactionType.DEPOSIT


def test_withdraw_decreases_balance():
    a = _new_usd()
    a.deposit(TransactionAmount.of_money(Money(Decimal("500"), Currency.USD)))
    a.withdraw(TransactionAmount.of_money(Money(Decimal("200"), Currency.USD)))
    assert a.balance.amount == Decimal("300")


def test_withdrawing_more_than_balance_throws():
    a = _new_usd()
    a.deposit(TransactionAmount.of_money(Money(Decimal("100"), Currency.USD)))
    with pytest.raises(AccountRuleViolation, match="Insufficient"):
        a.withdraw(TransactionAmount.of_money(Money(Decimal("200"), Currency.USD)))


def test_deposit_in_wrong_currency_throws():
    a = _new_usd()
    with pytest.raises(ValueError, match="match"):
        a.deposit(TransactionAmount.of_money(Money(Decimal("100"), Currency.EUR)))


def test_freeze_blocks_deposit():
    a = _new_usd()
    a.freeze()
    with pytest.raises(AccountRuleViolation, match="frozen"):
        a.deposit(TransactionAmount.of_money(Money(Decimal("100"), Currency.USD)))


def test_close_is_terminal():
    a = _new_usd()
    a.close()
    with pytest.raises(AccountRuleViolation, match="closed"):
        a.freeze()


def test_transfer_out_with_fee_deducts_total():
    a = _new_usd()
    a.deposit(TransactionAmount.of_money(Money(Decimal("1000"), Currency.USD)))
    a.transfer_out(TransactionAmount.of_money(Money(Decimal("200"), Currency.USD)), Money(Decimal("2"), Currency.USD), uuid4())
    assert a.balance.amount == Decimal("798")
