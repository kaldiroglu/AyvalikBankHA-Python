from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ....application.service import AccountApplicationService
from ....domain.model import Money, TransactionAmount
from ....domain.port.in_.ports import (
    ICustomerAccountPort,
)
from ....domain.port.in_.ports import ICustomerAccountPort
from .deps import get_account_service, require_customer
from .dto import (
    AccountResponse,
    BalanceResponse,
    CreateCheckingAccountRequest,
    CreateSavingsAccountRequest,
    CreateTimeDepositAccountRequest,
    MoneyOperationRequest,
    TransactionResponse,
    TransferRequest,
)

router = APIRouter(prefix="/api", tags=["account"])


@router.post("/accounts/checking", status_code=201, response_model=AccountResponse)
async def create_checking(
    body: CreateCheckingAccountRequest,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    od = Money(body.overdraft_limit or 0, body.currency)
    a = await service.open_checking(
        ICustomerAccountPort.OpenCheckingCommand(caller_id=caller.id, currency=body.currency, overdraft_limit=od)
    )
    return AccountResponse.from_domain(a)


@router.post("/accounts/savings", status_code=201, response_model=AccountResponse)
async def create_savings(
    body: CreateSavingsAccountRequest,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    a = await service.open_savings(
        ICustomerAccountPort.OpenSavingsCommand(
            caller_id=caller.id, currency=body.currency, annual_interest_rate=body.annual_interest_rate
        )
    )
    return AccountResponse.from_domain(a)


@router.post("/accounts/time-deposit", status_code=201, response_model=AccountResponse)
async def create_time_deposit(
    body: CreateTimeDepositAccountRequest,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    a = await service.open_time_deposit(
        ICustomerAccountPort.OpenTimeDepositCommand(
            caller_id=caller.id,
            currency=body.currency,
            principal=Money(body.principal, body.currency),
            maturity_date=body.maturity_date,
            annual_interest_rate=body.annual_interest_rate,
        )
    )
    return AccountResponse.from_domain(a)


@router.get("/customers/{customer_id}/accounts", response_model=list[AccountResponse])
async def list_accounts(
    customer_id: UUID,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    accounts = await service.list_accounts(caller.id, customer_id)
    return [AccountResponse.from_domain(a) for a in accounts]


@router.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: UUID,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    return BalanceResponse.from_domain(await service.get_balance(caller.id, account_id))


@router.post("/accounts/{account_id}/deposit", status_code=201, response_model=TransactionResponse)
async def deposit(
    account_id: UUID,
    body: MoneyOperationRequest,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    tx = await service.deposit(
        ICustomerAccountPort.DepositCommand(caller_id=caller.id, account_id=account_id, amount=TransactionAmount.of(body.amount, body.currency))
    )
    return TransactionResponse.from_domain(tx)


@router.post("/accounts/{account_id}/withdraw", status_code=201, response_model=TransactionResponse)
async def withdraw(
    account_id: UUID,
    body: MoneyOperationRequest,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    tx = await service.withdraw(
        ICustomerAccountPort.WithdrawCommand(caller_id=caller.id, account_id=account_id, amount=TransactionAmount.of(body.amount, body.currency))
    )
    return TransactionResponse.from_domain(tx)


@router.post("/accounts/{account_id}/transfer", status_code=200)
async def transfer(
    account_id: UUID,
    body: TransferRequest,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    await service.transfer(
        ICustomerAccountPort.TransferCommand(
            caller_id=caller.id,
            source_account_id=account_id,
            target_account_id=body.target_account_id,
            amount=TransactionAmount.of(body.amount, body.currency),
        )
    )
    return {"status": "ok"}


@router.get("/accounts/{account_id}/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    account_id: UUID,
    service: Annotated[ICustomerAccountPort, Depends(get_account_service)],
    caller=Depends(require_customer),
):
    txs = await service.get_transactions(caller.id, account_id)
    return [TransactionResponse.from_domain(t) for t in txs]
