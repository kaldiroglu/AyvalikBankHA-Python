from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from .account_state import AccountState
from .account_status import AccountStatus
from .account_type import AccountType
from .currency import Currency
from .money import Money
from .transaction_amount import TransactionAmount
from .transaction import Transaction
from .transaction_type import TransactionType


class Account(ABC):
    """Rich domain entity. Owns its own invariants via the State pattern + per-type
    behavior in CheckingAccount / SavingsAccount / TimeDepositAccount subclasses."""

    def __init__(
        self,
        id: UUID,
        owner_id: UUID,
        currency: Currency,
        balance: Money,
        status: AccountStatus,
    ) -> None:
        if balance.currency != currency:
            raise ValueError("Balance currency must match account currency")
        self._id = id
        self._owner_id = owner_id
        self._currency = currency
        self._balance = balance
        self._state: AccountState = AccountState.of(status)

    # ── Read-only identity / value properties ───────────────────────────

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def owner_id(self) -> UUID:
        return self._owner_id

    @property
    def currency(self) -> Currency:
        return self._currency

    @property
    def balance(self) -> Money:
        return self._balance

    @property
    def status(self) -> AccountStatus:
        return self._state.status

    @property
    def is_terminal(self) -> bool:
        return self._state.is_terminal

    @property
    @abstractmethod
    def type(self) -> AccountType: ...

    # ── Status transitions (delegated to State) ──────────────────────────

    def freeze(self) -> None:
        self._state = self._state.freeze()

    def unfreeze(self) -> None:
        self._state = self._state.unfreeze()

    def close(self) -> None:
        self._state = self._state.close()

    def _require_operable(self) -> None:
        self._state.require_operable()

    # ── Operations: subtypes override ────────────────────────────────────

    @abstractmethod
    def deposit(self, amount: TransactionAmount) -> Transaction: ...

    @abstractmethod
    def withdraw(self, amount: TransactionAmount) -> Transaction: ...

    @abstractmethod
    def transfer_out(self, amount: TransactionAmount, fee: Money, target_account_id: UUID) -> Transaction: ...

    def transfer_in(self, amount: TransactionAmount, source_account_id: UUID) -> Transaction:
        self._require_operable()
        self._require_same_currency(amount)
        self._balance = self._balance.add(amount.value)
        return Transaction.create(
            self._id,
            TransactionType.TRANSFER_IN,
            amount.value,
            f"Transfer in from {source_account_id}",
        )

    # ── Guards ────────────────────────────────────────────────────────────

    def _require_same_currency(self, amount: Money) -> None:
        if amount.currency != self._currency:
            raise ValueError(
                f"Currency {amount.currency} does not match account currency {self._currency}"
            )
