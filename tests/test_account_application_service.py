"""Orchestration tests for the application service.

Ported from AyvalikBankHA-JAVA's AccountApplicationServiceTest. These cannot be replaced by the
shared HTTP contract suite: they assert which port was called and which exception type was
raised, not just the resulting status code.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from ayvalikbank_ha.domain.model import TransactionAmount

from ayvalikbank_ha.application.exception import (
    AccountNotOperableException,
    InsufficientFundsException,
    InvalidAccountOperationException,
    LimitExceededException,
    NotFoundException,
)
from ayvalikbank_ha.application.service.account_application_service import (
    AccountApplicationService,
)
from ayvalikbank_ha.domain.model import (
    CheckingAccount,
    Currency,
    Customer,
    CustomerTier,
    Money,
    SavingsAccount,
    TransactionType,
)
from ayvalikbank_ha.domain.port.in_.ports import (
    IAccountAdministrationPort,
    ICustomerAccountPort,
)
from ayvalikbank_ha.domain.service import TransferDomainService


class _Accounts:
    def __init__(self) -> None:
        self.by_id: dict[UUID, object] = {}
        self.saved: list[object] = []

    def add(self, account):
        self.by_id[account.id] = account
        return account

    async def find_by_id(self, account_id):
        return self.by_id.get(account_id)

    async def save(self, account):
        self.saved.append(account)
        self.by_id[account.id] = account
        return account

    async def list_by_owner(self, owner_id):
        return [a for a in self.by_id.values() if a.owner_id == owner_id]


class _Customers:
    def __init__(self) -> None:
        self.by_id: dict[UUID, Customer] = {}

    def add(self, tier: CustomerTier = CustomerTier.STANDARD) -> Customer:
        c = Customer.create("X", f"{uuid4()}@x.dev", "hash")
        c.change_tier(tier)
        self.by_id[c.id] = c
        return c

    async def find_by_id(self, customer_id):
        return self.by_id.get(customer_id)

    async def exists_by_id(self, customer_id):
        return customer_id in self.by_id


class _Transactions:
    def __init__(self) -> None:
        self.saved: list[object] = []

    async def save(self, tx):
        self.saved.append(tx)
        return tx

    async def list_by_account(self, account_id):
        return list(self.saved)


class _Settings:
    def __init__(self, percent: Decimal = Decimal("1.0")) -> None:
        self.percent = percent

    async def get_transfer_fee_percent(self):
        return self.percent

    async def set_transfer_fee_percent(self, percent):
        self.percent = percent


@pytest.fixture
def accounts() -> _Accounts:
    return _Accounts()


@pytest.fixture
def customers() -> _Customers:
    return _Customers()


@pytest.fixture
def transactions() -> _Transactions:
    return _Transactions()


@pytest.fixture
def settings() -> _Settings:
    return _Settings()


@pytest.fixture
def service(accounts, customers, transactions, settings) -> AccountApplicationService:
    return AccountApplicationService(
        accounts, customers, transactions, settings, TransferDomainService()
    )


def _checking(accounts, owner_id, balance: str = "0") -> CheckingAccount:
    a = CheckingAccount.open(owner_id, Currency.USD)
    if Decimal(balance) > 0:
        a.deposit(TransactionAmount.of_money(Money(Decimal(balance), Currency.USD)))
    return accounts.add(a)


# ── opening ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_opens_checking_for_an_existing_customer(service, customers, accounts):
    owner = customers.add()

    a = await service.open_checking(
        ICustomerAccountPort.OpenCheckingCommand(
            caller_id=owner.id, currency=Currency.USD, overdraft_limit=Money(Decimal("0"), Currency.USD)
        )
    )

    assert a.owner_id == owner.id
    assert accounts.saved


@pytest.mark.asyncio
async def test_opens_savings_for_an_existing_customer(service, customers):
    owner = customers.add()

    a = await service.open_savings(
        ICustomerAccountPort.OpenSavingsCommand(
            caller_id=owner.id, currency=Currency.USD, annual_interest_rate=Decimal("0.05")
        )
    )

    assert isinstance(a, SavingsAccount)


@pytest.mark.asyncio
async def test_opens_time_deposit_for_an_existing_customer(service, customers):
    owner = customers.add()

    a = await service.open_time_deposit(
        ICustomerAccountPort.OpenTimeDepositCommand(
            caller_id=owner.id,
            currency=Currency.USD,
            principal=Money(Decimal("1000"), Currency.USD),
            maturity_date=date.today() + timedelta(days=365),
            annual_interest_rate=Decimal("0.05"),
        )
    )

    assert a.owner_id == owner.id


@pytest.mark.asyncio
async def test_opening_for_a_missing_customer_is_not_found(service):
    with pytest.raises(NotFoundException):
        await service.open_checking(
            ICustomerAccountPort.OpenCheckingCommand(
                caller_id=uuid4(), currency=Currency.USD,
                overdraft_limit=Money(Decimal("0"), Currency.USD),
            )
        )


# ── deposit / withdraw ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deposit_credits_the_account(service, customers, accounts, transactions):
    owner = customers.add()
    a = _checking(accounts, owner.id)

    tx = await service.deposit(
        ICustomerAccountPort.DepositCommand(
            caller_id=owner.id, account_id=a.id, amount=TransactionAmount.of_money(Money(Decimal("200"), Currency.USD))
        )
    )

    assert tx.type is TransactionType.DEPOSIT
    assert a.balance.amount == Decimal("200")
    assert transactions.saved


@pytest.mark.asyncio
async def test_deposit_into_a_missing_account_is_not_found(service):
    with pytest.raises(NotFoundException):
        await service.deposit(
            ICustomerAccountPort.DepositCommand(
                caller_id=uuid4(), account_id=uuid4(), amount=TransactionAmount.of_money(Money(Decimal("100"), Currency.USD))
            )
        )


@pytest.mark.asyncio
async def test_withdrawal_beyond_the_balance_is_rejected(service, customers, accounts):
    owner = customers.add()
    a = _checking(accounts, owner.id, "100")

    with pytest.raises(InsufficientFundsException):
        await service.withdraw(
            ICustomerAccountPort.WithdrawCommand(
                caller_id=owner.id, account_id=a.id, amount=TransactionAmount.of_money(Money(Decimal("500"), Currency.USD))
            )
        )


@pytest.mark.asyncio
async def test_withdrawal_from_a_frozen_account_is_not_operable(service, customers, accounts):
    owner = customers.add()
    a = _checking(accounts, owner.id, "500")
    a.freeze()

    with pytest.raises(AccountNotOperableException):
        await service.withdraw(
            ICustomerAccountPort.WithdrawCommand(
                caller_id=owner.id, account_id=a.id, amount=TransactionAmount.of_money(Money(Decimal("10"), Currency.USD))
            )
        )


# ── transfer and fees ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transfer_between_one_customers_own_accounts_is_free(service, customers, accounts):
    owner = customers.add()
    src = _checking(accounts, owner.id, "500")
    tgt = _checking(accounts, owner.id)

    await service.transfer(
        ICustomerAccountPort.TransferCommand(
            caller_id=owner.id, source_account_id=src.id, target_account_id=tgt.id,
            amount=TransactionAmount.of_money(Money(Decimal("200"), Currency.USD)),
        )
    )

    assert src.balance.amount == Decimal("300")
    assert tgt.balance.amount == Decimal("200")


@pytest.mark.asyncio
async def test_transfer_between_different_customers_deducts_the_fee(service, customers, accounts):
    sender = customers.add()
    recipient = customers.add()
    src = _checking(accounts, sender.id, "1000")
    tgt = _checking(accounts, recipient.id)

    await service.transfer(
        ICustomerAccountPort.TransferCommand(
            caller_id=sender.id, source_account_id=src.id, target_account_id=tgt.id,
            amount=TransactionAmount.of_money(Money(Decimal("200"), Currency.USD)),
        )
    )

    assert src.balance.amount == Decimal("798")
    assert tgt.balance.amount == Decimal("200")


@pytest.mark.asyncio
async def test_premium_tier_halves_the_transfer_fee(service, customers, accounts):
    sender = customers.add(CustomerTier.PREMIUM)
    recipient = customers.add()
    src = _checking(accounts, sender.id, "1000")
    tgt = _checking(accounts, recipient.id)

    await service.transfer(
        ICustomerAccountPort.TransferCommand(
            caller_id=sender.id, source_account_id=src.id, target_account_id=tgt.id,
            amount=TransactionAmount.of_money(Money(Decimal("200"), Currency.USD)),
        )
    )

    assert src.balance.amount == Decimal("799")


@pytest.mark.asyncio
async def test_transfer_above_the_standard_cap_is_rejected(service, customers, accounts):
    sender = customers.add()
    recipient = customers.add()
    src = _checking(accounts, sender.id, "10000")
    tgt = _checking(accounts, recipient.id)

    with pytest.raises(LimitExceededException):
        await service.transfer(
            ICustomerAccountPort.TransferCommand(
                caller_id=sender.id, source_account_id=src.id, target_account_id=tgt.id,
                amount=TransactionAmount.of_money(Money(Decimal("5001"), Currency.USD)),
            )
        )


@pytest.mark.asyncio
async def test_withdrawal_above_the_standard_cap_is_rejected(service, customers, accounts):
    owner = customers.add()
    a = _checking(accounts, owner.id, "10000")

    with pytest.raises(LimitExceededException):
        await service.withdraw(
            ICustomerAccountPort.WithdrawCommand(
                caller_id=owner.id, account_id=a.id, amount=TransactionAmount.of_money(Money(Decimal("5001"), Currency.USD))
            )
        )


# ── status transitions ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_freezes_then_unfreezes(service, customers, accounts):
    a = _checking(accounts, customers.add().id)

    await service.freeze_account(a.id)
    assert a.status.name == "FROZEN"

    await service.unfreeze_account(a.id)
    assert a.status.name == "ACTIVE"


@pytest.mark.asyncio
async def test_closes_an_account(service, customers, accounts):
    a = _checking(accounts, customers.add().id)

    await service.close_account(a.id)

    assert a.status.name == "CLOSED"


@pytest.mark.asyncio
async def test_freezing_a_closed_account_is_not_operable(service, customers, accounts):
    a = _checking(accounts, customers.add().id)
    await service.close_account(a.id)

    with pytest.raises(AccountNotOperableException):
        await service.freeze_account(a.id)


@pytest.mark.asyncio
async def test_freezing_a_missing_account_is_not_found(service):
    with pytest.raises(NotFoundException):
        await service.freeze_account(uuid4())


# ── interest and maturity ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accrues_interest_on_a_savings_account(service, customers, accounts):
    owner = customers.add()
    s = SavingsAccount.open(owner.id, Currency.USD, Decimal("0.12"))
    s.deposit(TransactionAmount.of_money(Money(Decimal("1000"), Currency.USD)))
    accounts.add(s)

    tx = await service.accrue_interest(
        IAccountAdministrationPort.AccrueInterestCommand(account_id=s.id, year=2026, month=4)
    )

    assert tx.type is TransactionType.INTEREST
    assert s.balance.amount > Decimal("1000")


@pytest.mark.asyncio
async def test_accruing_on_a_non_savings_account_is_rejected(service, customers, accounts):
    a = _checking(accounts, customers.add().id)

    with pytest.raises(InvalidAccountOperationException):
        await service.accrue_interest(
            IAccountAdministrationPort.AccrueInterestCommand(account_id=a.id, year=2026, month=4)
        )


@pytest.mark.asyncio
async def test_maturing_a_non_time_deposit_is_rejected(service, customers, accounts):
    a = _checking(accounts, customers.add().id)

    with pytest.raises(InvalidAccountOperationException):
        await service.mature_time_deposit(a.id)


# ── bank settings ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stores_the_transfer_fee_percent(service, settings):
    await service.set_transfer_fee(Decimal("2.50"))

    assert settings.percent == Decimal("2.50")


@pytest.mark.asyncio
async def test_rejects_a_negative_transfer_fee_percent(service, settings):
    with pytest.raises(InvalidAccountOperationException):
        await service.set_transfer_fee(Decimal("-0.01"))

    assert settings.percent == Decimal("1.0")
