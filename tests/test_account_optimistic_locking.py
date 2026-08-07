"""Optimistic locking on accounts.

No threads, no sleeps. A lost update is a *stale-read* problem, not a timing problem, so two
sessions committing in a fixed order reproduce it deterministically.

Mirrors AyvalikBankHA-JAVA Refactorings.md entry 5.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm.exc import StaleDataError

from ayvalikbank_ha.adapter.out.persistence.db import Base
from ayvalikbank_ha.adapter.out.persistence.entity.jpa_entities import (
    AccountJpaEntity,
    CustomerJpaEntity,
)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


async def _seed(Session) -> AccountJpaEntity:
    owner = CustomerJpaEntity(
        id=uuid4(), name="alice", email=f"a-{uuid4()}@x.com", role="CUSTOMER",
        tier="STANDARD", current_password_hash="h",
    )
    account = AccountJpaEntity(
        id=uuid4(), owner_id=owner.id, currency="USD", balance=Decimal("100"),
        status="ACTIVE", type="CHECKING", overdraft_limit=Decimal("0"),
    )
    async with Session() as s:
        s.add(owner)
        s.add(account)
        await s.commit()
    return account


@pytest.mark.asyncio
async def test_new_account_starts_at_version_one(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    a = await _seed(Session)
    async with Session() as s:
        # SQLAlchemy's version_id_col starts at 1, unlike Hibernate's @Version which starts at 0.
        assert (await s.get(AccountJpaEntity, a.id)).version == 1


@pytest.mark.asyncio
async def test_version_increments_on_each_update(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    a = await _seed(Session)

    for expected in (2, 3):
        async with Session() as s:
            loaded = await s.get(AccountJpaEntity, a.id)
            loaded.balance = Decimal(f"10{expected}")
            await s.commit()
        async with Session() as s:
            assert (await s.get(AccountJpaEntity, a.id)).version == expected


@pytest.mark.asyncio
async def test_second_writer_is_rejected_when_both_loaded_the_same_version(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    a = await _seed(Session)

    s1 = Session()
    s2 = Session()
    # Both read balance 100 at the same version — this is the stale read.
    first = await s1.get(AccountJpaEntity, a.id)
    second = await s2.get(AccountJpaEntity, a.id)

    first.balance = Decimal("50")
    await s1.commit()

    second.balance = Decimal("50")
    with pytest.raises(StaleDataError):
        await s2.commit()

    await s1.close()
    await s2.close()

    # Without the version both writers would have stored 50 and one withdrawal would be lost.
    async with Session() as s:
        assert (await s.get(AccountJpaEntity, a.id)).balance == Decimal("50")
