from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapter.out.persistence.entity import CustomerJpaEntity
from ..domain.model import Customer
from ..domain.port.out import IPasswordHasherPort

ADMIN_EMAIL = "admin@ayvalikbank.dev"
ADMIN_PASSWORD = "Admin@123!"


async def seed_admin(session: AsyncSession, hasher: IPasswordHasherPort) -> None:
    existing = await session.execute(
        select(CustomerJpaEntity).where(CustomerJpaEntity.email == ADMIN_EMAIL)
    )
    if existing.scalar_one_or_none() is not None:
        return
    admin = Customer.create("Administrator", ADMIN_EMAIL, hasher.hash(ADMIN_PASSWORD))
    admin.role = "ADMIN"  # default Customer.create sets CUSTOMER
    session.add(
        CustomerJpaEntity(
            id=admin.id,
            name=admin.name,
            email=admin.email,
            role="ADMIN",
            tier="STANDARD",
            current_password_hash=admin.current_password_hash,
        )
    )
    await session.commit()
