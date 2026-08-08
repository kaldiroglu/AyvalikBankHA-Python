"""Ownership authorization on customer-facing account operations.

Any authenticated customer could previously operate on any account given its id, and set any
other customer's password. Mirrors AyvalikBankHA-JAVA Refactorings.md entry 3.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from ayvalikbank_ha.domain.model import TransactionAmount

from ayvalikbank_ha.application.exception import UnauthorizedAccessException
from ayvalikbank_ha.application.service.account_application_service import (
    AccountApplicationService,
)
from ayvalikbank_ha.domain.model import CheckingAccount, Currency, Money
from ayvalikbank_ha.domain.port.in_ import (
    IDepositMoneyUseCase,
    ITransferMoneyUseCase,
    IWithdrawMoneyUseCase,
)


class _Accounts:
    def __init__(self) -> None:
        self.by_id: dict[UUID, CheckingAccount] = {}
        self.saved: list[CheckingAccount] = []

    def add(self, account: CheckingAccount) -> CheckingAccount:
        self.by_id[account.id] = account
        return account

    async def find_by_id(self, account_id: UUID):
        return self.by_id.get(account_id)

    async def save(self, account):
        self.saved.append(account)
        return account

    async def list_by_owner(self, owner_id: UUID):
        return [a for a in self.by_id.values() if a.owner_id == owner_id]


class _Empty:
    async def find_by_id(self, _id):
        return None

    async def save(self, x):
        return x

    async def list_by_account(self, _id):
        return []

    async def get_transfer_fee_percent(self):
        return Decimal("1.0")


@pytest.fixture
def accounts() -> _Accounts:
    return _Accounts()


@pytest.fixture
def service(accounts: _Accounts) -> AccountApplicationService:
    from ayvalikbank_ha.domain.service import TransferDomainService

    return AccountApplicationService(accounts, _Empty(), _Empty(), _Empty(), TransferDomainService())


@pytest.mark.asyncio
async def test_deposit_into_another_customers_account_is_rejected(service, accounts):
    account = accounts.add(CheckingAccount.open(uuid4(), Currency.USD))

    with pytest.raises(UnauthorizedAccessException):
        await service.deposit(
            IDepositMoneyUseCase.Command(
                caller_id=uuid4(), account_id=account.id, amount=TransactionAmount.of_money(Money(Decimal("100"), Currency.USD))
            )
        )
    assert accounts.saved == []


@pytest.mark.asyncio
async def test_withdrawal_from_another_customers_account_is_rejected(service, accounts):
    account = accounts.add(CheckingAccount.open(uuid4(), Currency.USD))

    with pytest.raises(UnauthorizedAccessException):
        await service.withdraw(
            IWithdrawMoneyUseCase.Command(
                caller_id=uuid4(), account_id=account.id, amount=TransactionAmount.of_money(Money(Decimal("10"), Currency.USD))
            )
        )
    assert accounts.saved == []


@pytest.mark.asyncio
async def test_transfer_out_of_another_customers_account_is_rejected(service, accounts):
    intruder = uuid4()
    source = accounts.add(CheckingAccount.open(uuid4(), Currency.USD))
    target = accounts.add(CheckingAccount.open(intruder, Currency.USD))

    with pytest.raises(UnauthorizedAccessException):
        await service.transfer(
            ITransferMoneyUseCase.Command(
                caller_id=intruder,
                source_account_id=source.id,
                target_account_id=target.id,
                amount=TransactionAmount.of_money(Money(Decimal("10"), Currency.USD)),
            )
        )
    assert accounts.saved == []


@pytest.mark.asyncio
async def test_reading_another_customers_balance_is_rejected(service, accounts):
    account = accounts.add(CheckingAccount.open(uuid4(), Currency.USD))

    with pytest.raises(UnauthorizedAccessException):
        await service.get_balance(uuid4(), account.id)


@pytest.mark.asyncio
async def test_reading_another_customers_transactions_is_rejected(service, accounts):
    account = accounts.add(CheckingAccount.open(uuid4(), Currency.USD))

    with pytest.raises(UnauthorizedAccessException):
        await service.get_transactions(uuid4(), account.id)


@pytest.mark.asyncio
async def test_listing_another_customers_accounts_is_rejected(service):
    with pytest.raises(UnauthorizedAccessException):
        await service.list_accounts(uuid4(), uuid4())
