from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

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


class _CamelModel(BaseModel):
    """Base for every request and response DTO.

    The wire format is **camelCase** in all six implementations, so a client written against any
    one of them works against all of them. Python attribute names stay snake_case; Pydantic's
    alias generator bridges the two. `populate_by_name` keeps snake_case construction working in
    tests and internal code.

    See AyvalikBankContractTests - the shared HTTP contract suite that pins this.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


# ── Requests ───────────────────────────────────────────────────────────────


class CreateCustomerRequest(_CamelModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str


class ChangePasswordRequest(_CamelModel):
    new_password: str


class ChangeCustomerTierRequest(_CamelModel):
    tier: CustomerTier


class CreateCheckingAccountRequest(_CamelModel):
    currency: Currency
    overdraft_limit: Decimal | None = Field(default=None, ge=0)


class CreateSavingsAccountRequest(_CamelModel):
    currency: Currency
    annual_interest_rate: Decimal = Field(ge=0, le=10)


class CreateTimeDepositAccountRequest(_CamelModel):
    currency: Currency
    principal: Decimal = Field(gt=0)
    maturity_date: date
    annual_interest_rate: Decimal = Field(ge=0, le=10)


class AccrueInterestRequest(_CamelModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class MoneyOperationRequest(_CamelModel):
    amount: Decimal = Field(gt=0)
    currency: Currency


class TransferRequest(_CamelModel):
    target_account_id: UUID
    amount: Decimal = Field(gt=0)
    currency: Currency


class SetTransferFeeRequest(_CamelModel):
    fee_percent: Decimal = Field(ge=0, le=100)


# ── Responses ──────────────────────────────────────────────────────────────


class CustomerResponse(_CamelModel):
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


class AccountResponse(_CamelModel):
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


class BalanceResponse(_CamelModel):
    amount: Decimal
    currency: str

    @staticmethod
    def from_domain(m: Money) -> "BalanceResponse":
        return BalanceResponse(amount=m.amount, currency=m.currency.value)


class TransactionResponse(_CamelModel):
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
