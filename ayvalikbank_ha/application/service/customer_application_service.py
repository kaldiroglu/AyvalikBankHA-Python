from __future__ import annotations

from uuid import UUID

from ...domain.model import Customer, CustomerTier
from ...domain.port.in_ import (
    IChangeCustomerTierUseCase,
    IChangePasswordUseCase,
    ICreateCustomerUseCase,
    IDeleteCustomerUseCase,
    IListCustomersUseCase,
)
from ...domain.port.out import ICustomerRepositoryPort, IPasswordHasherPort
from ...domain.service import PasswordValidationService
from ..exception import (
    InvalidCredentialsException,
    NotFoundException,
    PasswordReuseException,
    PasswordValidationException,
)

_PASSWORD_HISTORY = 3


class CustomerApplicationService(
    ICreateCustomerUseCase,
    IDeleteCustomerUseCase,
    IListCustomersUseCase,
    IChangePasswordUseCase,
    IChangeCustomerTierUseCase,
):
    def __init__(
        self,
        customer_repo: ICustomerRepositoryPort,
        hasher: IPasswordHasherPort,
        password_validator: PasswordValidationService,
    ) -> None:
        self._customers = customer_repo
        self._hasher = hasher
        self._validator = password_validator

    async def create_customer(self, cmd: ICreateCustomerUseCase.Command) -> Customer:
        try:
            self._validator.validate(cmd.password)
        except ValueError as e:
            raise PasswordValidationException(str(e)) from e
        existing = await self._customers.find_by_email(cmd.email)
        if existing is not None:
            raise InvalidCredentialsException(f"Email already in use: {cmd.email}")
        password_hash = self._hasher.hash(cmd.password)
        c = Customer.create(cmd.name, cmd.email, password_hash)
        return await self._customers.save(c)

    async def delete_customer(self, customer_id: UUID) -> None:
        existing = await self._customers.find_by_id(customer_id)
        if existing is None:
            raise NotFoundException(f"Customer {customer_id} not found")
        await self._customers.delete(customer_id)

    async def list_customers(self) -> list[Customer]:
        return await self._customers.list_all()

    async def change_password(self, cmd: IChangePasswordUseCase.Command) -> None:
        try:
            self._validator.validate(cmd.new_password)
        except ValueError as e:
            raise PasswordValidationException(str(e)) from e
        customer = await self._customers.find_by_id(cmd.customer_id)
        if customer is None:
            raise NotFoundException(f"Customer {cmd.customer_id} not found")
        history = await self._customers.previous_password_hashes(cmd.customer_id)
        all_hashes = [customer.current_password_hash, *history]
        for h in all_hashes:
            if self._hasher.matches(cmd.new_password, h):
                raise PasswordReuseException("Password was used recently")
        old_hash = customer.current_password_hash
        customer.change_password(self._hasher.hash(cmd.new_password))
        await self._customers.save(customer)
        await self._customers.push_previous_password_hash(cmd.customer_id, old_hash)

    async def change_customer_tier(self, cmd: IChangeCustomerTierUseCase.Command) -> None:
        customer = await self._customers.find_by_id(cmd.customer_id)
        if customer is None:
            raise NotFoundException(f"Customer {cmd.customer_id} not found")
        customer.change_tier(cmd.new_tier)
        await self._customers.save(customer)
