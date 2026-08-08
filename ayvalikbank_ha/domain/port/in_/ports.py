"""Driving (in) ports, grouped by **actor**.

A port is one conversation with one kind of outside actor (Cockburn) — not one method, and not one
aggregate. The previous twenty single-method Protocols segregated nothing: a customer-facing
controller uses all nine customer-facing methods, so splitting them bought no Interface Segregation
while giving the account controller nine dependencies and the admin controller ten.

Where ISP genuinely bites is the actor boundary — the admin controller must not depend on deposit
and withdraw — and that is the split these five ports make.

Mirrors AyvalikBankHA-JAVA Refactorings.md entry 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from ...model import (
    Account,
    Currency,
    Customer,
    CustomerTier,
    Money,
    Transaction,
    TransactionAmount,
)


class ICustomerAccountPort(Protocol):
    """Everything a customer can do with their own accounts."""

    @dataclass(frozen=True)
    class OpenCheckingCommand:
        caller_id: UUID
        currency: Currency
        overdraft_limit: Money

    @dataclass(frozen=True)
    class OpenSavingsCommand:
        caller_id: UUID
        currency: Currency
        annual_interest_rate: Decimal

    @dataclass(frozen=True)
    class OpenTimeDepositCommand:
        caller_id: UUID
        currency: Currency
        principal: Money
        maturity_date: date
        annual_interest_rate: Decimal

    @dataclass(frozen=True)
    class DepositCommand:
        caller_id: UUID
        account_id: UUID
        amount: TransactionAmount

    @dataclass(frozen=True)
    class WithdrawCommand:
        caller_id: UUID
        account_id: UUID
        amount: TransactionAmount

    @dataclass(frozen=True)
    class TransferCommand:
        caller_id: UUID
        source_account_id: UUID
        target_account_id: UUID
        amount: TransactionAmount

    async def open_checking(self, cmd: "ICustomerAccountPort.OpenCheckingCommand") -> Account: ...
    async def open_savings(self, cmd: "ICustomerAccountPort.OpenSavingsCommand") -> Account: ...
    async def open_time_deposit(self, cmd: "ICustomerAccountPort.OpenTimeDepositCommand") -> Account: ...
    async def deposit(self, cmd: "ICustomerAccountPort.DepositCommand") -> Transaction: ...
    async def withdraw(self, cmd: "ICustomerAccountPort.WithdrawCommand") -> Transaction: ...
    async def transfer(self, cmd: "ICustomerAccountPort.TransferCommand") -> None: ...
    async def get_balance(self, caller_id: UUID, account_id: UUID) -> Money: ...
    async def list_accounts(self, caller_id: UUID, customer_id: UUID) -> list[Account]: ...
    async def get_transactions(self, caller_id: UUID, account_id: UUID) -> list[Transaction]: ...


class IAccountAdministrationPort(Protocol):
    """Everything an administrator can do to an account they do not own."""

    @dataclass(frozen=True)
    class AccrueInterestCommand:
        account_id: UUID
        year: int
        month: int

    async def freeze_account(self, account_id: UUID) -> None: ...
    async def unfreeze_account(self, account_id: UUID) -> None: ...
    async def close_account(self, account_id: UUID) -> None: ...
    async def accrue_interest(self, cmd: "IAccountAdministrationPort.AccrueInterestCommand") -> Transaction: ...
    async def mature_time_deposit(self, account_id: UUID) -> Transaction: ...


class IBankSettingsPort(Protocol):
    """Bank-wide configuration an administrator can change."""

    async def set_transfer_fee(self, fee_percent: Decimal) -> None: ...


class ICustomerAdministrationPort(Protocol):
    """Everything an administrator can do to the customer roster."""

    @dataclass(frozen=True)
    class CreateCustomerCommand:
        name: str
        email: str
        password: str

    @dataclass(frozen=True)
    class ChangeCustomerTierCommand:
        customer_id: UUID
        new_tier: CustomerTier

    async def create_customer(self, cmd: "ICustomerAdministrationPort.CreateCustomerCommand") -> Customer: ...
    async def delete_customer(self, customer_id: UUID) -> None: ...
    async def list_customers(self) -> list[Customer]: ...
    async def change_customer_tier(self, cmd: "ICustomerAdministrationPort.ChangeCustomerTierCommand") -> None: ...


class ICustomerSelfServicePort(Protocol):
    """What a customer can do to their own record."""

    @dataclass(frozen=True)
    class ChangePasswordCommand:
        caller_id: UUID
        customer_id: UUID
        new_password: str

    async def change_password(self, cmd: "ICustomerSelfServicePort.ChangePasswordCommand") -> None: ...
