from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from .account import Account
from .account_status import AccountStatus
from .account_type import AccountType
from .currency import Currency
from .money import Money
from .transaction import Transaction
from .transaction_type import TransactionType
from .rule_violation import (
    AccountNotActiveException,
    InsufficientBalanceException,
    OperationNotPermittedException,
)


class SavingsAccount(Account):
    _MONTHS_PER_YEAR = 12

    def __init__(
        self,
        id: UUID,
        owner_id: UUID,
        currency: Currency,
        balance: Money,
        status: AccountStatus,
        annual_interest_rate: Decimal,
        last_accrual_date: date | None,
    ) -> None:
        super().__init__(id, owner_id, currency, balance, status)
        if annual_interest_rate < Decimal("0"):
            raise ValueError("Annual interest rate must be non-negative")
        self._annual_interest_rate = annual_interest_rate
        self._last_accrual_date = last_accrual_date

    @staticmethod
    def open(owner_id: UUID, currency: Currency, annual_interest_rate: Decimal) -> "SavingsAccount":
        return SavingsAccount(
            uuid4(),
            owner_id,
            currency,
            Money.zero(currency),
            AccountStatus.ACTIVE,
            annual_interest_rate,
            None,
        )

    @property
    def type(self) -> AccountType:
        return AccountType.SAVINGS

    @property
    def annual_interest_rate(self) -> Decimal:
        return self._annual_interest_rate

    @property
    def last_accrual_date(self) -> date | None:
        return self._last_accrual_date

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
        if not self._balance.is_greater_than_or_equal_to(amount):
            raise InsufficientBalanceException("Insufficient funds")
        self._balance = self._balance.subtract(amount)
        return Transaction.create(self._id, TransactionType.WITHDRAWAL, amount, "Withdrawal")

    def transfer_out(self, amount: Money, fee: Money, target_account_id: UUID) -> Transaction:
        self._require_operable()
        self._require_same_currency(amount)
        total_debit = amount.add(fee) if fee.amount > Decimal("0") else amount
        if not self._balance.is_greater_than_or_equal_to(total_debit):
            raise InsufficientBalanceException("Insufficient funds for transfer including fee")
        self._balance = self._balance.subtract(total_debit)
        desc = f"Transfer out to {target_account_id}"
        if fee.amount > Decimal("0"):
            desc += f" (fee: {fee.amount})"
        return Transaction.create(self._id, TransactionType.TRANSFER_OUT, amount, desc)

    def accrue_interest(self, year: int, month: int) -> Transaction:
        # FROZEN accounts can still accrue: it's a system action, not a customer action.
        if self.is_terminal:
            raise AccountNotActiveException("Cannot accrue interest on a closed account")
        if month == 12:
            first_of_next_month = date(year + 1, 1, 1)
        else:
            first_of_next_month = date(year, month + 1, 1)
        if self._last_accrual_date is not None and first_of_next_month <= self._last_accrual_date:
            raise OperationNotPermittedException(f"Interest already accrued for or after {year:04d}-{month:02d}")

        monthly_rate = self._annual_interest_rate / Decimal(self._MONTHS_PER_YEAR)
        interest_amount = (self._balance.amount * monthly_rate).quantize(Decimal("0.01"))
        interest = Money(interest_amount, self._currency)
        self._balance = self._balance.add(interest)
        self._last_accrual_date = first_of_next_month
        return Transaction.create(
            self._id,
            TransactionType.INTEREST,
            interest,
            f"Interest accrual for {year:04d}-{month:02d}",
        )
