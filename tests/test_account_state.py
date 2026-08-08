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
)


def _new_active() -> CheckingAccount:
    return CheckingAccount.open(uuid4(), Currency.USD)


def test_new_account_is_active():
    a = _new_active()
    assert a.status is AccountStatus.ACTIVE
    assert a.is_terminal is False


def test_freeze_moves_to_frozen():
    a = _new_active()
    a.freeze()
    assert a.status is AccountStatus.FROZEN


def test_unfreeze_moves_frozen_to_active():
    a = _new_active()
    a.freeze()
    a.unfreeze()
    assert a.status is AccountStatus.ACTIVE


def test_freezing_frozen_throws():
    a = _new_active()
    a.freeze()
    with pytest.raises(AccountRuleViolation, match="already frozen"):
        a.freeze()


def test_unfreezing_active_throws():
    a = _new_active()
    with pytest.raises(AccountRuleViolation, match="not frozen"):
        a.unfreeze()


def test_close_from_active_is_terminal():
    a = _new_active()
    a.close()
    assert a.status is AccountStatus.CLOSED
    assert a.is_terminal is True


def test_close_from_frozen_is_terminal():
    a = _new_active()
    a.freeze()
    a.close()
    assert a.status is AccountStatus.CLOSED


def test_closed_rejects_all_transitions():
    a = _new_active()
    a.close()
    with pytest.raises(AccountRuleViolation, match="closed"):
        a.freeze()
    with pytest.raises(AccountRuleViolation, match="closed"):
        a.unfreeze()
    with pytest.raises(AccountRuleViolation, match="already closed"):
        a.close()


def test_frozen_blocks_deposit():
    a = _new_active()
    a.freeze()
    with pytest.raises(AccountRuleViolation, match="frozen"):
        a.deposit(TransactionAmount.of_money(Money(Decimal("100"), Currency.USD)))


def test_frozen_blocks_withdraw():
    a = _new_active()
    a.deposit(TransactionAmount.of_money(Money(Decimal("100"), Currency.USD)))
    a.freeze()
    with pytest.raises(AccountRuleViolation, match="frozen"):
        a.withdraw(TransactionAmount.of_money(Money(Decimal("50"), Currency.USD)))


def test_closed_blocks_deposit():
    a = _new_active()
    a.close()
    with pytest.raises(AccountRuleViolation, match="closed"):
        a.deposit(TransactionAmount.of_money(Money(Decimal("100"), Currency.USD)))
