from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from ...domain.model import (
    Account,
    CheckingAccount,
    Money,
    SavingsAccount,
    TimeDepositAccount,
    Transaction,
)
from ...domain.port.in_ import (
    IAccrueInterestUseCase,
    ICloseAccountUseCase,
    IDepositMoneyUseCase,
    IFreezeAccountUseCase,
    IGetBalanceUseCase,
    IGetTransactionsUseCase,
    IListAccountsUseCase,
    IMatureTimeDepositUseCase,
    IOpenCheckingAccountUseCase,
    IOpenSavingsAccountUseCase,
    IOpenTimeDepositAccountUseCase,
    ISetTransferFeeUseCase,
    ITransferMoneyUseCase,
    IUnfreezeAccountUseCase,
    IWithdrawMoneyUseCase,
)
from ...domain.port.out import (
    IAccountRepositoryPort,
    ICustomerRepositoryPort,
    ISettingsRepositoryPort,
    ITransactionRepositoryPort,
)
from ...domain.service import TransferDomainService
from ..exception import (
    AccountNotOperableException,
    InsufficientFundsException,
    InvalidAccountOperationException,
    LimitExceededException,
    NotFoundException,
)


class AccountApplicationService(
    IOpenCheckingAccountUseCase,
    IOpenSavingsAccountUseCase,
    IOpenTimeDepositAccountUseCase,
    IDepositMoneyUseCase,
    IWithdrawMoneyUseCase,
    ITransferMoneyUseCase,
    IGetBalanceUseCase,
    IGetTransactionsUseCase,
    IListAccountsUseCase,
    IFreezeAccountUseCase,
    IUnfreezeAccountUseCase,
    ICloseAccountUseCase,
    IAccrueInterestUseCase,
    IMatureTimeDepositUseCase,
    ISetTransferFeeUseCase,
):
    def __init__(
        self,
        account_repo: IAccountRepositoryPort,
        customer_repo: ICustomerRepositoryPort,
        transaction_repo: ITransactionRepositoryPort,
        settings_repo: ISettingsRepositoryPort,
        transfer_service: TransferDomainService,
    ) -> None:
        self._accounts = account_repo
        self._customers = customer_repo
        self._transactions = transaction_repo
        self._settings = settings_repo
        self._transfer = transfer_service

    # ── opens ─────────────────────────────────────────────────────────────

    async def open_checking(self, cmd: IOpenCheckingAccountUseCase.Command) -> Account:
        await self._require_customer(cmd.owner_id)
        a = CheckingAccount.open(cmd.owner_id, cmd.currency, cmd.overdraft_limit)
        return await self._accounts.save(a)

    async def open_savings(self, cmd: IOpenSavingsAccountUseCase.Command) -> Account:
        await self._require_customer(cmd.owner_id)
        a = SavingsAccount.open(cmd.owner_id, cmd.currency, cmd.annual_interest_rate)
        return await self._accounts.save(a)

    async def open_time_deposit(self, cmd: IOpenTimeDepositAccountUseCase.Command) -> Account:
        await self._require_customer(cmd.owner_id)
        a = TimeDepositAccount.open(
            cmd.owner_id,
            cmd.currency,
            cmd.principal,
            cmd.maturity_date,
            cmd.annual_interest_rate,
        )
        return await self._accounts.save(a)

    # ── money ops ─────────────────────────────────────────────────────────

    async def deposit(self, cmd: IDepositMoneyUseCase.Command) -> Transaction:
        a = await self._require_account(cmd.account_id)
        try:
            tx = a.deposit(cmd.amount)
        except PermissionError as e:
            self._reraise_permission(e)
        except ValueError as e:
            raise InvalidAccountOperationException(str(e)) from e
        await self._accounts.save(a)
        return await self._transactions.save(tx)

    async def withdraw(self, cmd: IWithdrawMoneyUseCase.Command) -> Transaction:
        a = await self._require_account(cmd.account_id)
        owner = await self._require_customer(a.owner_id)
        try:
            self._transfer.require_withdrawal_within_limit(cmd.amount, owner.tier)
        except PermissionError as e:
            raise LimitExceededException(str(e)) from e
        try:
            tx = a.withdraw(cmd.amount)
        except PermissionError as e:
            self._reraise_permission(e)
        except ValueError as e:
            raise InvalidAccountOperationException(str(e)) from e
        await self._accounts.save(a)
        return await self._transactions.save(tx)

    async def transfer(self, cmd: ITransferMoneyUseCase.Command) -> None:
        if cmd.source_account_id == cmd.target_account_id:
            raise InvalidAccountOperationException("Cannot transfer to the same account")
        source = await self._require_account(cmd.source_account_id)
        target = await self._require_account(cmd.target_account_id)
        source_owner = await self._require_customer(source.owner_id)

        try:
            self._transfer.require_transfer_within_limit(cmd.amount, source_owner.tier)
        except PermissionError as e:
            raise LimitExceededException(str(e)) from e

        same_customer = source.owner_id == target.owner_id
        fee_percent = await self._settings.get_transfer_fee_percent()
        fee = self._transfer.calculate_fee(
            cmd.amount, same_customer, fee_percent, source_owner.tier
        )

        try:
            out_tx = source.transfer_out(cmd.amount, fee, target.id)
            in_tx = target.transfer_in(cmd.amount, source.id)
        except PermissionError as e:
            self._reraise_permission(e)
        except ValueError as e:
            raise InvalidAccountOperationException(str(e)) from e

        await self._accounts.save(source)
        await self._accounts.save(target)
        await self._transactions.save(out_tx)
        await self._transactions.save(in_tx)

    # ── reads ─────────────────────────────────────────────────────────────

    async def get_balance(self, account_id: UUID) -> Money:
        a = await self._require_account(account_id)
        return a.balance

    async def get_transactions(self, account_id: UUID) -> list[Transaction]:
        await self._require_account(account_id)
        return await self._transactions.list_by_account(account_id)

    async def list_accounts(self, customer_id: UUID) -> list[Account]:
        await self._require_customer(customer_id)
        return await self._accounts.list_by_owner(customer_id)

    # ── status transitions ───────────────────────────────────────────────

    async def freeze_account(self, account_id: UUID) -> None:
        a = await self._require_account(account_id)
        try:
            a.freeze()
        except PermissionError as e:
            raise AccountNotOperableException(str(e)) from e
        await self._accounts.save(a)

    async def unfreeze_account(self, account_id: UUID) -> None:
        a = await self._require_account(account_id)
        try:
            a.unfreeze()
        except PermissionError as e:
            raise AccountNotOperableException(str(e)) from e
        await self._accounts.save(a)

    async def close_account(self, account_id: UUID) -> None:
        a = await self._require_account(account_id)
        try:
            a.close()
        except PermissionError as e:
            raise AccountNotOperableException(str(e)) from e
        await self._accounts.save(a)

    # ── interest / maturity ──────────────────────────────────────────────

    async def accrue_interest(self, cmd: IAccrueInterestUseCase.Command) -> Transaction:
        a = await self._require_account(cmd.account_id)
        if not isinstance(a, SavingsAccount):
            raise InvalidAccountOperationException(
                "Interest accrual only applies to savings accounts"
            )
        try:
            tx = a.accrue_interest(cmd.year, cmd.month)
        except PermissionError as e:
            raise InvalidAccountOperationException(str(e)) from e
        await self._accounts.save(a)
        return await self._transactions.save(tx)

    async def mature_time_deposit(self, account_id: UUID) -> Transaction:
        a = await self._require_account(account_id)
        if not isinstance(a, TimeDepositAccount):
            raise InvalidAccountOperationException(
                "Maturity only applies to time deposit accounts"
            )
        today = datetime.now(timezone.utc).date()
        try:
            tx = a.mature(today)
        except PermissionError as e:
            raise InvalidAccountOperationException(str(e)) from e
        await self._accounts.save(a)
        return await self._transactions.save(tx)

    # ── admin: settings ─────────────────────────────────────────────────

    async def set_transfer_fee(self, fee_percent) -> None:
        if fee_percent < 0 or fee_percent > 100:
            raise InvalidAccountOperationException("Transfer fee percent must be between 0 and 100")
        await self._settings.set_transfer_fee_percent(fee_percent)

    # ── helpers ──────────────────────────────────────────────────────────

    async def _require_account(self, account_id: UUID) -> Account:
        a = await self._accounts.find_by_id(account_id)
        if a is None:
            raise NotFoundException(f"Account {account_id} not found")
        return a

    async def _require_customer(self, customer_id: UUID):
        c = await self._customers.find_by_id(customer_id)
        if c is None:
            raise NotFoundException(f"Customer {customer_id} not found")
        return c

    @staticmethod
    def _reraise_permission(e: PermissionError) -> None:
        msg = str(e)
        if msg.startswith("Insufficient"):
            raise InsufficientFundsException(msg) from e
        if "frozen" in msg.lower() or "closed" in msg.lower():
            raise AccountNotOperableException(msg) from e
        raise InvalidAccountOperationException(msg) from e
