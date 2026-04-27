from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.model import Account, Customer, Transaction
from ..entity import (
    AccountJpaEntity,
    CustomerJpaEntity,
    PasswordHistoryJpaEntity,
    SettingsJpaEntity,
    TransactionJpaEntity,
)
from ..mapper import AccountMapper, CustomerMapper, TransactionMapper

_TRANSFER_FEE_KEY = "transfer_fee_percent"
_PASSWORD_HISTORY_LIMIT = 3


class CustomerPersistenceAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, customer_id: UUID) -> Customer | None:
        e = await self._session.get(CustomerJpaEntity, customer_id)
        return CustomerMapper.to_domain(e) if e else None

    async def find_by_email(self, email: str) -> Customer | None:
        result = await self._session.execute(
            select(CustomerJpaEntity).where(CustomerJpaEntity.email == email)
        )
        e = result.scalar_one_or_none()
        return CustomerMapper.to_domain(e) if e else None

    async def list_all(self) -> list[Customer]:
        result = await self._session.execute(select(CustomerJpaEntity))
        return [CustomerMapper.to_domain(e) for e in result.scalars().all()]

    async def save(self, customer: Customer) -> Customer:
        existing = await self._session.get(CustomerJpaEntity, customer.id)
        if existing is None:
            self._session.add(CustomerMapper.to_jpa(customer))
        else:
            existing.name = customer.name
            existing.email = customer.email
            existing.role = customer.role
            existing.tier = customer.tier.value
            existing.current_password_hash = customer.current_password_hash
        await self._session.flush()
        return customer

    async def delete(self, customer_id: UUID) -> None:
        await self._session.execute(
            delete(PasswordHistoryJpaEntity).where(
                PasswordHistoryJpaEntity.customer_id == customer_id
            )
        )
        await self._session.execute(
            delete(CustomerJpaEntity).where(CustomerJpaEntity.id == customer_id)
        )
        await self._session.flush()

    async def previous_password_hashes(self, customer_id: UUID) -> list[str]:
        result = await self._session.execute(
            select(PasswordHistoryJpaEntity)
            .where(PasswordHistoryJpaEntity.customer_id == customer_id)
            .order_by(PasswordHistoryJpaEntity.created_at.desc())
            .limit(_PASSWORD_HISTORY_LIMIT)
        )
        return [e.password_hash for e in result.scalars().all()]

    async def push_previous_password_hash(self, customer_id: UUID, hash_: str) -> None:
        self._session.add(
            PasswordHistoryJpaEntity(
                customer_id=customer_id,
                password_hash=hash_,
                created_at=datetime.now(timezone.utc),
            )
        )
        # Trim history to the most recent N
        result = await self._session.execute(
            select(PasswordHistoryJpaEntity)
            .where(PasswordHistoryJpaEntity.customer_id == customer_id)
            .order_by(PasswordHistoryJpaEntity.created_at.desc())
        )
        rows = list(result.scalars().all())
        for stale in rows[_PASSWORD_HISTORY_LIMIT:]:
            await self._session.delete(stale)
        await self._session.flush()


class AccountPersistenceAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, account_id: UUID) -> Account | None:
        e = await self._session.get(AccountJpaEntity, account_id)
        return AccountMapper.to_domain(e) if e else None

    async def list_by_owner(self, owner_id: UUID) -> list[Account]:
        result = await self._session.execute(
            select(AccountJpaEntity).where(AccountJpaEntity.owner_id == owner_id)
        )
        return [AccountMapper.to_domain(e) for e in result.scalars().all()]

    async def save(self, account: Account) -> Account:
        existing = await self._session.get(AccountJpaEntity, account.id)
        if existing is None:
            self._session.add(AccountMapper.to_jpa(account))
        else:
            AccountMapper.apply_to(account, existing)
        await self._session.flush()
        return account


class TransactionPersistenceAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, transaction: Transaction) -> Transaction:
        self._session.add(TransactionMapper.to_jpa(transaction))
        await self._session.flush()
        return transaction

    async def list_by_account(self, account_id: UUID) -> list[Transaction]:
        result = await self._session.execute(
            select(TransactionJpaEntity)
            .where(TransactionJpaEntity.account_id == account_id)
            .order_by(TransactionJpaEntity.timestamp.desc())
        )
        return [TransactionMapper.to_domain(e) for e in result.scalars().all()]


class SettingsPersistenceAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_transfer_fee_percent(self) -> Decimal:
        e = await self._session.get(SettingsJpaEntity, _TRANSFER_FEE_KEY)
        return Decimal(e.value) if e else Decimal("0")

    async def set_transfer_fee_percent(self, percent: Decimal) -> None:
        existing = await self._session.get(SettingsJpaEntity, _TRANSFER_FEE_KEY)
        if existing is None:
            self._session.add(SettingsJpaEntity(key=_TRANSFER_FEE_KEY, value=str(percent)))
        else:
            existing.value = str(percent)
        await self._session.flush()
