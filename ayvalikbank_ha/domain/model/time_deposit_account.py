from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .account import Account
from .account_status import AccountStatus
from .account_type import AccountType
from .currency import Currency
from .money import Money
from .transaction import Transaction
from .transaction_type import TransactionType


class TimeDepositAccount(Account):
    def __init__(
        self,
        id: UUID,
        owner_id: UUID,
        currency: Currency,
        balance: Money,
        status: AccountStatus,
        principal: Money,
        opened_on: date,
        maturity_date: date,
        annual_interest_rate: Decimal,
        matured: bool,
    ) -> None:
        super().__init__(id, owner_id, currency, balance, status)
        if principal.currency != currency:
            raise ValueError("Principal currency must match account currency")
        if principal.amount <= Decimal("0"):
            raise ValueError("Principal must be positive")
        if annual_interest_rate < Decimal("0"):
            raise ValueError("Annual interest rate must be non-negative")
        if maturity_date <= opened_on:
            raise ValueError("Maturity date must be after opened-on date")
        self._principal = principal
        self._opened_on = opened_on
        self._maturity_date = maturity_date
        self._annual_interest_rate = annual_interest_rate
        self._matured = matured

    @staticmethod
    def open(
        owner_id: UUID,
        currency: Currency,
        principal: Money,
        maturity_date: date,
        annual_interest_rate: Decimal,
    ) -> "TimeDepositAccount":
        opened_on = datetime.now(timezone.utc).date()
        return TimeDepositAccount(
            uuid4(),
            owner_id,
            currency,
            principal,
            AccountStatus.ACTIVE,
            principal,
            opened_on,
            maturity_date,
            annual_interest_rate,
            False,
        )

    @property
    def type(self) -> AccountType:
        return AccountType.TIME_DEPOSIT

    @property
    def principal(self) -> Money:
        return self._principal

    @property
    def opened_on(self) -> date:
        return self._opened_on

    @property
    def maturity_date(self) -> date:
        return self._maturity_date

    @property
    def annual_interest_rate(self) -> Decimal:
        return self._annual_interest_rate

    @property
    def matured(self) -> bool:
        return self._matured

    def deposit(self, amount: Money) -> Transaction:
        raise PermissionError("Time deposit principal is locked — further deposits are not allowed")

    def transfer_out(self, amount: Money, fee: Money, target_account_id: UUID) -> Transaction:
        raise PermissionError("Time deposit accounts do not support transfers")

    def withdraw(self, amount: Money) -> Transaction:
        self._require_operable()
        if not self._matured:
            raise PermissionError("Time deposit has not matured")
        self._require_same_currency(amount)
        if amount.amount <= Decimal("0"):
            raise ValueError("Withdrawal amount must be positive")
        if not self._balance.is_greater_than_or_equal_to(amount):
            raise PermissionError("Insufficient funds")
        self._balance = self._balance.subtract(amount)
        return Transaction.create(self._id, TransactionType.WITHDRAWAL, amount, "Withdrawal")

    def mature(self, today: date) -> Transaction:
        # FROZEN accounts can still mature: it's a date-driven system action.
        if self.is_terminal:
            raise PermissionError("Cannot mature a closed account")
        if self._matured:
            raise PermissionError("Account is already matured")
        if today < self._maturity_date:
            raise PermissionError("Maturity date not yet reached")

        months = (self._maturity_date.year - self._opened_on.year) * 12 + (
            self._maturity_date.month - self._opened_on.month
        )
        years = Decimal(months) / Decimal(12)
        interest_amount = (self._principal.amount * self._annual_interest_rate * years).quantize(
            Decimal("0.01")
        )
        interest = Money(interest_amount, self._currency)
        self._balance = self._balance.add(interest)
        self._matured = True
        return Transaction.create(
            self._id, TransactionType.INTEREST, interest, "Maturity interest credit"
        )
