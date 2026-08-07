"""SQLAlchemy entities — they implement the persistence schema and never cross
the persistence boundary. The mapper module converts them to/from domain entities."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _uuid() -> type:
    # SQLAlchemy 2.0's generic Uuid type works on both Postgres (native UUID)
    # and SQLite (stored as CHAR(32)).
    return Uuid(as_uuid=True)


class CustomerJpaEntity(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(_uuid(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False, default="STANDARD")
    current_password_hash: Mapped[str] = mapped_column(
        "current_password", String(120), nullable=False
    )


class PasswordHistoryJpaEntity(Base):
    __tablename__ = "password_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[UUID] = mapped_column(_uuid(), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccountJpaEntity(Base):
    __tablename__ = "accounts"

    # Optimistic-lock token, managed entirely by SQLAlchemy.
    #
    # Without it two concurrent withdrawals both read the same balance, both write their own
    # result, and one silently disappears while both transaction rows persist - leaving the
    # balance disagreeing with the ledger.
    # Mirrors AyvalikBankHA-JAVA Refactorings.md entry 5.
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    id: Mapped[UUID] = mapped_column(_uuid(), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(
        _uuid(), ForeignKey("customers.id"), nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(19, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    # Single-table inheritance: discriminator + nullable type-specific columns
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    overdraft_limit: Mapped[Decimal | None] = mapped_column(Numeric(19, 2), nullable=True)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(19, 4), nullable=True)
    last_accrual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    principal: Mapped[Decimal | None] = mapped_column(Numeric(19, 2), nullable=True)
    opened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    matured: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    __mapper_args__ = {"version_id_col": version}


class TransactionJpaEntity(Base):
    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(_uuid(), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        _uuid(), ForeignKey("accounts.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class SettingsJpaEntity(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
