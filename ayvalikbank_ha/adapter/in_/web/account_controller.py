from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from ....application.service import AccountApplicationService
from ....domain.model import Money
from ....domain.port.in_ import (
    IDepositMoneyUseCase,
    IOpenCheckingAccountUseCase,
    IOpenSavingsAccountUseCase,
    IOpenTimeDepositAccountUseCase,
    ITransferMoneyUseCase,
    IWithdrawMoneyUseCase,
)
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

router = APIRouter(prefix="/api", tags=["account"], dependencies=[Depends(require_customer)])


@router.post("/accounts/checking", status_code=201, response_model=AccountResponse)
async def create_checking(
    owner_id: UUID,
    body: CreateCheckingAccountRequest,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    od = Money(body.overdraft_limit or 0, body.currency)
    a = await service.open_checking(
        IOpenCheckingAccountUseCase.Command(owner_id=owner_id, currency=body.currency, overdraft_limit=od)
    )
    return AccountResponse.from_domain(a)


@router.post("/accounts/savings", status_code=201, response_model=AccountResponse)
async def create_savings(
    owner_id: UUID,
    body: CreateSavingsAccountRequest,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    a = await service.open_savings(
        IOpenSavingsAccountUseCase.Command(
            owner_id=owner_id, currency=body.currency, annual_interest_rate=body.annual_interest_rate
        )
    )
    return AccountResponse.from_domain(a)


@router.post("/accounts/time-deposit", status_code=201, response_model=AccountResponse)
async def create_time_deposit(
    owner_id: UUID,
    body: CreateTimeDepositAccountRequest,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    a = await service.open_time_deposit(
        IOpenTimeDepositAccountUseCase.Command(
            owner_id=owner_id,
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
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    accounts = await service.list_accounts(customer_id)
    return [AccountResponse.from_domain(a) for a in accounts]


@router.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: UUID,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    return BalanceResponse.from_domain(await service.get_balance(account_id))


@router.post("/accounts/{account_id}/deposit", status_code=201, response_model=TransactionResponse)
async def deposit(
    account_id: UUID,
    body: MoneyOperationRequest,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    tx = await service.deposit(
        IDepositMoneyUseCase.Command(account_id=account_id, amount=Money(body.amount, body.currency))
    )
    return TransactionResponse.from_domain(tx)


@router.post("/accounts/{account_id}/withdraw", status_code=201, response_model=TransactionResponse)
async def withdraw(
    account_id: UUID,
    body: MoneyOperationRequest,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    tx = await service.withdraw(
        IWithdrawMoneyUseCase.Command(account_id=account_id, amount=Money(body.amount, body.currency))
    )
    return TransactionResponse.from_domain(tx)


@router.post("/accounts/{account_id}/transfer", status_code=200)
async def transfer(
    account_id: UUID,
    body: TransferRequest,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    await service.transfer(
        ITransferMoneyUseCase.Command(
            source_account_id=account_id,
            target_account_id=body.target_account_id,
            amount=Money(body.amount, body.currency),
        )
    )
    return {"status": "ok"}


@router.get("/accounts/{account_id}/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    account_id: UUID,
    service: Annotated[AccountApplicationService, Depends(get_account_service)],
):
    txs = await service.get_transactions(account_id)
    return [TransactionResponse.from_domain(t) for t in txs]
