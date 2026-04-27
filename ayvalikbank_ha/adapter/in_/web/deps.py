"""DI / dependency-providers for FastAPI controllers.

The actual provider functions are bound in main.py at composition time.
Controllers Depend(...) on the names exported here; main.py overrides them via
app.dependency_overrides so the controllers stay decoupled from the engine config.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ....application.service import (
    AccountApplicationService,
    CustomerApplicationService,
)


# ── Service providers (overridden in main.py) ──────────────────────────────


async def get_account_service() -> AccountApplicationService:  # pragma: no cover
    raise NotImplementedError("Override in composition root")


async def get_customer_service() -> CustomerApplicationService:  # pragma: no cover
    raise NotImplementedError("Override in composition root")


# ── HTTP Basic auth ────────────────────────────────────────────────────────

_basic = HTTPBasic(auto_error=False)


async def authenticate(
    creds: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
    customer_service: Annotated[CustomerApplicationService, Depends(get_customer_service)],
):
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    customer_repo = customer_service._customers  # type: ignore[attr-defined]
    hasher = customer_service._hasher  # type: ignore[attr-defined]
    customer = await customer_repo.find_by_email(creds.username)
    if customer is None or not hasher.matches(creds.password, customer.current_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return customer


def require_role(*roles: str):
    async def _dep(customer=Depends(authenticate)):
        if customer.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
        return customer

    return _dep


require_admin = require_role("ADMIN")
require_customer = require_role("CUSTOMER", "ADMIN")
