from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ....application.service import AccountApplicationService, CustomerApplicationService
from ....domain.port.in_.ports import (
    IAccountAdministrationPort,
    ICustomerAdministrationPort,
)
from .deps import get_account_service, get_customer_service, require_admin
from .dto import (
    AccrueInterestRequest,
    ChangeCustomerTierRequest,
    CreateCustomerRequest,
    CustomerResponse,
    SetTransferFeeRequest,
    TransactionResponse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/customers", status_code=201, response_model=CustomerResponse)
async def create_customer(
    body: CreateCustomerRequest,
    service: Annotated[ICustomerAdministrationPort, Depends(get_customer_service)],
):
    c = await service.create_customer(
        ICustomerAdministrationPort.CreateCustomerCommand(name=body.name, email=body.email, password=body.password)
    )
    return CustomerResponse.from_domain(c)


@router.delete("/customers/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: UUID,
    service: Annotated[ICustomerAdministrationPort, Depends(get_customer_service)],
):
    await service.delete_customer(customer_id)


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    service: Annotated[ICustomerAdministrationPort, Depends(get_customer_service)],
):
    customers = await service.list_customers()
    return [CustomerResponse.from_domain(c) for c in customers]


@router.put("/customers/{customer_id}/tier", status_code=200)
async def change_tier(
    customer_id: UUID,
    body: ChangeCustomerTierRequest,
    service: Annotated[ICustomerAdministrationPort, Depends(get_customer_service)],
):
    await service.change_customer_tier(
        ICustomerAdministrationPort.ChangeCustomerTierCommand(customer_id=customer_id, new_tier=body.tier)
    )
    return {"status": "ok"}


@router.put("/settings/transfer-fee", status_code=200)
async def set_transfer_fee(
    body: SetTransferFeeRequest,
    service: Annotated[IBankSettingsPort, Depends(get_account_service)],
):
    await service.set_transfer_fee(body.fee_percent)
    return {"status": "ok"}


@router.put("/accounts/{account_id}/freeze", status_code=200)
async def freeze(
    account_id: UUID,
    service: Annotated[IAccountAdministrationPort, Depends(get_account_service)],
):
    await service.freeze_account(account_id)
    return {"status": "ok"}


@router.put("/accounts/{account_id}/unfreeze", status_code=200)
async def unfreeze(
    account_id: UUID,
    service: Annotated[IAccountAdministrationPort, Depends(get_account_service)],
):
    await service.unfreeze_account(account_id)
    return {"status": "ok"}


@router.put("/accounts/{account_id}/close", status_code=200)
async def close(
    account_id: UUID,
    service: Annotated[IAccountAdministrationPort, Depends(get_account_service)],
):
    await service.close_account(account_id)
    return {"status": "ok"}


@router.put("/accounts/{account_id}/accrue-interest", status_code=200, response_model=TransactionResponse)
async def accrue_interest(
    account_id: UUID,
    body: AccrueInterestRequest,
    service: Annotated[IAccountAdministrationPort, Depends(get_account_service)],
):
    tx = await service.accrue_interest(
        IAccountAdministrationPort.AccrueInterestCommand(account_id=account_id, year=body.year, month=body.month)
    )
    return TransactionResponse.from_domain(tx)


@router.put("/accounts/{account_id}/mature", status_code=200, response_model=TransactionResponse)
async def mature(
    account_id: UUID,
    service: Annotated[IAccountAdministrationPort, Depends(get_account_service)],
):
    tx = await service.mature_time_deposit(account_id)
    return TransactionResponse.from_domain(tx)
