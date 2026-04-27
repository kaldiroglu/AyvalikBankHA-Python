from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from .account import Account
from .account_status import AccountStatus
from .account_type import AccountType
from .currency import Currency
from .money import Money
from .transaction import Transaction
from .transaction_type import TransactionType


class CheckingAccount(Account):
    def __init__(
        self,
        id: UUID,
        owner_id: UUID,
        currency: Currency,
        balance: Money,
        status: AccountStatus,
        overdraft_limit: Money,
    ) -> None:
        super().__init__(id, owner_id, currency, balance, status)
        if overdraft_limit.currency != currency:
            raise ValueError("Overdraft limit currency must match account currency")
        if overdraft_limit.amount < Decimal("0"):
            raise ValueError("Overdraft limit cannot be negative")
        self._overdraft_limit = overdraft_limit

    @staticmethod
    def open(
        owner_id: UUID,
        currency: Currency,
        overdraft_limit: Money | None = None,
    ) -> "CheckingAccount":
        return CheckingAccount(
            uuid4(),
            owner_id,
            currency,
            Money.zero(currency),
            AccountStatus.ACTIVE,
            overdraft_limit if overdraft_limit is not None else Money.zero(currency),
        )

    @property
    def type(self) -> AccountType:
        return AccountType.CHECKING

    @property
    def overdraft_limit(self) -> Money:
        return self._overdraft_limit

    def deposit(self, amount: Money) -> Transaction:
        self._require_operable()
        self._require_same_currency(amount)
        if amount.amount <= Decimal("0"):
            raise ValueError("Deposit amount must be positive")
        self._balance = self._balance.add(amount)
        return Transaction.create(self._id, TransactionType.DEPOSIT, amount, "Deposit")

    def withdraw(self, amount: Money) -> Transaction:
        self._require_operable()
        self._require_same_currency(amount)
        if amount.amount <= Decimal("0"):
            raise ValueError("Withdrawal amount must be positive")
        projected = self._balance.amount - amount.amount
        floor = -self._overdraft_limit.amount
        if projected < floor:
            if self._overdraft_limit.amount == Decimal("0"):
                raise PermissionError("Insufficient funds")
            raise PermissionError("Withdrawal exceeds overdraft limit")
        self._balance = Money(projected, self._currency)
        return Transaction.create(self._id, TransactionType.WITHDRAWAL, amount, "Withdrawal")

    def transfer_out(self, amount: Money, fee: Money, target_account_id: UUID) -> Transaction:
        self._require_operable()
        self._require_same_currency(amount)
        total_debit = amount.add(fee) if fee.amount > Decimal("0") else amount
        projected = self._balance.amount - total_debit.amount
        floor = -self._overdraft_limit.amount
        if projected < floor:
            raise PermissionError("Insufficient funds for transfer including fee")
        self._balance = Money(projected, self._currency)
        desc = f"Transfer out to {target_account_id}"
        if fee.amount > Decimal("0"):
            desc += f" (fee: {fee.amount})"
        return Transaction.create(self._id, TransactionType.TRANSFER_OUT, amount, desc)
