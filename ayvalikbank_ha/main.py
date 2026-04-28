"""Composition root — wires concrete adapters into ports and assembles the FastAPI app."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

load_dotenv()

from .adapter.in_.web import (
    account_router,
    admin_router,
    customer_router,
    register_exception_handlers,
)
from .adapter.in_.web.deps import get_account_service, get_customer_service
from .adapter.out.persistence import Base, get_engine, get_sessionmaker
from .adapter.out.persistence.adapter import (
    AccountPersistenceAdapter,
    CustomerPersistenceAdapter,
    SettingsPersistenceAdapter,
    TransactionPersistenceAdapter,
)
from .adapter.out.security import BcryptPasswordHasherAdapter
from .application.service import AccountApplicationService, CustomerApplicationService
from .config import seed_admin
from .domain.service import PasswordValidationService, TransferDomainService

DEFAULT_DB_URL = "postgresql+asyncpg://bank:bank@localhost:5436/ayvalikbank"


def create_app(database_url: str | None = None) -> FastAPI:
    db_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    engine = get_engine(db_url)
    sessionmaker = get_sessionmaker(engine)
    hasher = BcryptPasswordHasherAdapter()
    password_validator = PasswordValidationService()
    transfer_service = TransferDomainService()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessionmaker() as session:
            await seed_admin(session, hasher)
        yield
        await engine.dispose()

    app = FastAPI(title="Ayvalık Bank HA-Python", lifespan=lifespan)
    register_exception_handlers(app)

    async def _customer_service():
        async with sessionmaker() as session:
            try:
                customer_repo = CustomerPersistenceAdapter(session)
                yield CustomerApplicationService(customer_repo, hasher, password_validator)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _account_service():
        async with sessionmaker() as session:
            try:
                account_repo = AccountPersistenceAdapter(session)
                customer_repo = CustomerPersistenceAdapter(session)
                tx_repo = TransactionPersistenceAdapter(session)
                settings_repo = SettingsPersistenceAdapter(session)
                yield AccountApplicationService(
                    account_repo, customer_repo, tx_repo, settings_repo, transfer_service
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_customer_service] = _customer_service
    app.dependency_overrides[get_account_service] = _account_service

    app.include_router(customer_router)
    app.include_router(account_router)
    app.include_router(admin_router)
    return app


app = create_app()
