from __future__ import annotations

from ....domain.model import (
    Account,
    AccountStatus,
    AccountType,
    CheckingAccount,
    Currency,
    Customer,
    CustomerTier,
    Money,
    SavingsAccount,
    TimeDepositAccount,
    Transaction,
    TransactionType,
)
from ..entity import AccountJpaEntity, CustomerJpaEntity, TransactionJpaEntity


class CustomerMapper:
    @staticmethod
    def to_domain(e: CustomerJpaEntity) -> Customer:
        return Customer(
            id=e.id,
            name=e.name,
            email=e.email,
            role=e.role,
            tier=CustomerTier(e.tier),
            current_password_hash=e.current_password_hash,
        )

    @staticmethod
    def to_jpa(c: Customer) -> CustomerJpaEntity:
        return CustomerJpaEntity(
            id=c.id,
            name=c.name,
            email=c.email,
            role=c.role,
            tier=c.tier.value,
            current_password_hash=c.current_password_hash,
        )


class AccountMapper:
    @staticmethod
    def to_domain(e: AccountJpaEntity) -> Account:
        currency = Currency(e.currency)
        balance = Money(e.balance, currency)
        status = AccountStatus(e.status)
        type_ = AccountType(e.type)
        if type_ is AccountType.CHECKING:
            return CheckingAccount(
                id=e.id,
                owner_id=e.owner_id,
                currency=currency,
                balance=balance,
                status=status,
                overdraft_limit=Money(e.overdraft_limit or 0, currency),
            )
        if type_ is AccountType.SAVINGS:
            return SavingsAccount(
                id=e.id,
                owner_id=e.owner_id,
                currency=currency,
                balance=balance,
                status=status,
                annual_interest_rate=e.interest_rate or 0,
                last_accrual_date=e.last_accrual_date,
            )
        if type_ is AccountType.TIME_DEPOSIT:
            return TimeDepositAccount(
                id=e.id,
                owner_id=e.owner_id,
                currency=currency,
                balance=balance,
                status=status,
                principal=Money(e.principal or 0, currency),
                opened_on=e.opened_on,
                maturity_date=e.maturity_date,
                annual_interest_rate=e.interest_rate or 0,
                matured=bool(e.matured),
            )
        raise ValueError(f"Unknown account type: {type_}")

    @staticmethod
    def to_jpa(a: Account) -> AccountJpaEntity:
        e = AccountJpaEntity(
            id=a.id,
            owner_id=a.owner_id,
            currency=a.currency.value,
            balance=a.balance.amount,
            status=a.status.value,
            type=a.type.value,
        )
        if isinstance(a, CheckingAccount):
            e.overdraft_limit = a.overdraft_limit.amount
        elif isinstance(a, SavingsAccount):
            e.interest_rate = a.annual_interest_rate
            e.last_accrual_date = a.last_accrual_date
        elif isinstance(a, TimeDepositAccount):
            e.principal = a.principal.amount
            e.opened_on = a.opened_on
            e.maturity_date = a.maturity_date
            e.interest_rate = a.annual_interest_rate
            e.matured = a.matured
        return e

    @staticmethod
    def apply_to(a: Account, e: AccountJpaEntity) -> None:
        """Copy mutable fields onto an already-loaded JpaEntity."""
        e.balance = a.balance.amount
        e.status = a.status.value
        if isinstance(a, CheckingAccount):
            e.overdraft_limit = a.overdraft_limit.amount
        elif isinstance(a, SavingsAccount):
            e.interest_rate = a.annual_interest_rate
            e.last_accrual_date = a.last_accrual_date
        elif isinstance(a, TimeDepositAccount):
            e.principal = a.principal.amount
            e.opened_on = a.opened_on
            e.maturity_date = a.maturity_date
            e.interest_rate = a.annual_interest_rate
            e.matured = a.matured


class TransactionMapper:
    @staticmethod
    def to_domain(e: TransactionJpaEntity) -> Transaction:
        currency = Currency(e.currency)
        return Transaction(
            id=e.id,
            account_id=e.account_id,
            type=TransactionType(e.type),
            amount=Money(e.amount, currency),
            timestamp=e.timestamp,
            description=e.description,
        )

    @staticmethod
    def to_jpa(t: Transaction) -> TransactionJpaEntity:
        return TransactionJpaEntity(
            id=t.id,
            account_id=t.account_id,
            type=t.type.value,
            amount=t.amount.amount,
            currency=t.amount.currency.value,
            timestamp=t.timestamp,
            description=t.description,
        )
