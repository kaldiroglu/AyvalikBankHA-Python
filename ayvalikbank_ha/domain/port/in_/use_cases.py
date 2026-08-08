"""Driving (in) ports — one Protocol per use case.
Controllers depend on these, not on the application service classes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from ...model import (
    TransactionAmount,
    Account,
    Currency,
    Customer,
    CustomerTier,
    Money,
    Transaction,
)

# ── Customer use cases ────────────────────────────────────────────────────


class ICreateCustomerUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        name: str
        email: str
        password: str

    async def create_customer(self, cmd: "ICreateCustomerUseCase.Command") -> Customer: ...


class IDeleteCustomerUseCase(Protocol):
    async def delete_customer(self, customer_id: UUID) -> None: ...


class IListCustomersUseCase(Protocol):
    async def list_customers(self) -> list[Customer]: ...


class IChangePasswordUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        customer_id: UUID
        new_password: str

    async def change_password(self, cmd: "IChangePasswordUseCase.Command") -> None: ...


class IChangeCustomerTierUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        customer_id: UUID
        new_tier: CustomerTier

    async def change_customer_tier(
        self, cmd: "IChangeCustomerTierUseCase.Command"
    ) -> None: ...


# ── Account use cases ─────────────────────────────────────────────────────


class IOpenCheckingAccountUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        currency: Currency
        overdraft_limit: Money

    async def open_checking(self, cmd: "IOpenCheckingAccountUseCase.Command") -> Account: ...


class IOpenSavingsAccountUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        currency: Currency
        annual_interest_rate: Decimal

    async def open_savings(self, cmd: "IOpenSavingsAccountUseCase.Command") -> Account: ...


class IOpenTimeDepositAccountUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        currency: Currency
        principal: Money
        maturity_date: date
        annual_interest_rate: Decimal

    async def open_time_deposit(
        self, cmd: "IOpenTimeDepositAccountUseCase.Command"
    ) -> Account: ...


class IDepositMoneyUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        account_id: UUID
        amount: TransactionAmount

    async def deposit(self, cmd: "IDepositMoneyUseCase.Command") -> Transaction: ...


class IWithdrawMoneyUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        account_id: UUID
        amount: TransactionAmount

    async def withdraw(self, cmd: "IWithdrawMoneyUseCase.Command") -> Transaction: ...


class ITransferMoneyUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        caller_id: UUID
        source_account_id: UUID
        target_account_id: UUID
        amount: TransactionAmount

    async def transfer(self, cmd: "ITransferMoneyUseCase.Command") -> None: ...


class IGetBalanceUseCase(Protocol):
    async def get_balance(self, caller_id: UUID, account_id: UUID) -> Money: ...


class IGetTransactionsUseCase(Protocol):
    async def get_transactions(self, caller_id: UUID, account_id: UUID) -> list[Transaction]: ...


class IListAccountsUseCase(Protocol):
    async def list_accounts(self, caller_id: UUID, customer_id: UUID) -> list[Account]: ...


class IFreezeAccountUseCase(Protocol):
    async def freeze_account(self, account_id: UUID) -> None: ...


class IUnfreezeAccountUseCase(Protocol):
    async def unfreeze_account(self, account_id: UUID) -> None: ...


class ICloseAccountUseCase(Protocol):
    async def close_account(self, account_id: UUID) -> None: ...


class IAccrueInterestUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        account_id: UUID
        year: int
        month: int

    async def accrue_interest(self, cmd: "IAccrueInterestUseCase.Command") -> Transaction: ...


class IMatureTimeDepositUseCase(Protocol):
    async def mature_time_deposit(self, account_id: UUID) -> Transaction: ...


class ISetTransferFeeUseCase(Protocol):
    async def set_transfer_fee(self, fee_percent: Decimal) -> None: ...


__all__ = [
    "ICreateCustomerUseCase",
    "IDeleteCustomerUseCase",
    "IListCustomersUseCase",
    "IChangePasswordUseCase",
    "IChangeCustomerTierUseCase",
    "IOpenCheckingAccountUseCase",
    "IOpenSavingsAccountUseCase",
    "IOpenTimeDepositAccountUseCase",
    "IDepositMoneyUseCase",
    "IWithdrawMoneyUseCase",
    "ITransferMoneyUseCase",
    "IGetBalanceUseCase",
    "IGetTransactionsUseCase",
    "IListAccountsUseCase",
    "IFreezeAccountUseCase",
    "IUnfreezeAccountUseCase",
    "ICloseAccountUseCase",
    "IAccrueInterestUseCase",
    "IMatureTimeDepositUseCase",
    "ISetTransferFeeUseCase",
]
