from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ....application.service import CustomerApplicationService
from ....domain.port.in_.ports import ICustomerSelfServicePort
from .deps import get_customer_service, require_customer
from .dto import ChangePasswordRequest

router = APIRouter(prefix="/api/customers", tags=["customer"])


@router.put("/{customer_id}/password", status_code=200)
async def change_password(
    customer_id: UUID,
    body: ChangePasswordRequest,
    service: Annotated[ICustomerSelfServicePort, Depends(get_customer_service)],
    caller=Depends(require_customer),
) -> dict[str, str]:
    await service.change_password(
        ICustomerSelfServicePort.ChangePasswordCommand(
            caller_id=caller.id, customer_id=customer_id, new_password=body.new_password
        )
    )
    return {"status": "ok"}
