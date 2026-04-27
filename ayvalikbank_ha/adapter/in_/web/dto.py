from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from ...out.persistence.mapper import AccountMapper  # noqa: F401 — keep import order stable
from ....domain.model import (
    Account,
    CheckingAccount,
    Customer,
    Currency,
    CustomerTier,
    Money,
    SavingsAccount,
    TimeDepositAccount,
    Transaction,
)


# ── Requests ───────────────────────────────────────────────────────────────


class CreateCustomerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str


class ChangeCustomerTierRequest(BaseModel):
    tier: CustomerTier


class CreateCheckingAccountRequest(BaseModel):
    currency: Currency
    overdraft_limit: Decimal | None = Field(default=None, ge=0)


class CreateSavingsAccountRequest(BaseModel):
    currency: Currency
    annual_interest_rate: Decimal = Field(ge=0, le=10)


class CreateTimeDepositAccountRequest(BaseModel):
    currency: Currency
    principal: Decimal = Field(gt=0)
    maturity_date: date
    annual_interest_rate: Decimal = Field(ge=0, le=10)


class AccrueInterestRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class MoneyOperationRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Currency


class TransferRequest(BaseModel):
    target_account_id: UUID
    amount: Decimal = Field(gt=0)
    currency: Currency


class SetTransferFeeRequest(BaseModel):
    fee_percent: Decimal = Field(ge=0, le=100)


# ── Responses ──────────────────────────────────────────────────────────────


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    tier: str

    @staticmethod
    def from_domain(c: Customer) -> "CustomerResponse":
        return CustomerResponse(
            id=c.id, name=c.name, email=c.email, role=c.role, tier=c.tier.value
        )


class AccountResponse(BaseModel):
    id: UUID
    owner_id: UUID
    currency: str
    balance: Decimal
    status: str
    type: str
    overdraft_limit: Decimal | None = None
    interest_rate: Decimal | None = None
    last_accrual_date: date | None = None
    principal: Decimal | None = None
    opened_on: date | None = None
    maturity_date: date | None = None
    matured: bool | None = None

    @staticmethod
    def from_domain(a: Account) -> "AccountResponse":
        base = dict(
            id=a.id,
            owner_id=a.owner_id,
            currency=a.currency.value,
            balance=a.balance.amount,
            status=a.status.value,
            type=a.type.value,
        )
        if isinstance(a, CheckingAccount):
            return AccountResponse(**base, overdraft_limit=a.overdraft_limit.amount)
        if isinstance(a, SavingsAccount):
            return AccountResponse(
                **base,
                interest_rate=a.annual_interest_rate,
                last_accrual_date=a.last_accrual_date,
            )
        if isinstance(a, TimeDepositAccount):
            return AccountResponse(
                **base,
                interest_rate=a.annual_interest_rate,
                principal=a.principal.amount,
                opened_on=a.opened_on,
                maturity_date=a.maturity_date,
                matured=a.matured,
            )
        return AccountResponse(**base)


class BalanceResponse(BaseModel):
    amount: Decimal
    currency: str

    @staticmethod
    def from_domain(m: Money) -> "BalanceResponse":
        return BalanceResponse(amount=m.amount, currency=m.currency.value)


class TransactionResponse(BaseModel):
    id: UUID
    account_id: UUID
    type: str
    amount: Decimal
    currency: str
    timestamp: datetime
    description: str

    @staticmethod
    def from_domain(t: Transaction) -> "TransactionResponse":
        return TransactionResponse(
            id=t.id,
            account_id=t.account_id,
            type=t.type.value,
            amount=t.amount.amount,
            currency=t.amount.currency.value,
            timestamp=t.timestamp,
            description=t.description,
        )
