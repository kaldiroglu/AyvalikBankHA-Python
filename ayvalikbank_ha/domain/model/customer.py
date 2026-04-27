from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .customer_tier import CustomerTier


@dataclass
class Customer:
    id: UUID
    name: str
    email: str
    role: str
    tier: CustomerTier
    current_password_hash: str

    @staticmethod
    def create(name: str, email: str, password_hash: str) -> "Customer":
        return Customer(
            id=uuid4(),
            name=name,
            email=email,
            role="CUSTOMER",
            tier=CustomerTier.STANDARD,
            current_password_hash=password_hash,
        )

    def change_password(self, new_hash: str) -> None:
        if not new_hash:
            raise ValueError("Hash must not be empty")
        self.current_password_hash = new_hash

    def change_tier(self, new_tier: CustomerTier) -> None:
        self.tier = new_tier
