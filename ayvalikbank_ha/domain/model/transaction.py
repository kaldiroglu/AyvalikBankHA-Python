from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .money import Money
from .transaction_type import TransactionType


@dataclass(frozen=True, slots=True)
class Transaction:
    id: UUID
    account_id: UUID
    type: TransactionType
    amount: Money
    timestamp: datetime
    description: str

    @staticmethod
    def create(
        account_id: UUID,
        type: TransactionType,
        amount: Money,
        description: str,
    ) -> "Transaction":
        return Transaction(
            id=uuid4(),
            account_id=account_id,
            type=type,
            amount=amount,
            timestamp=datetime.now(timezone.utc),
            description=description,
        )
