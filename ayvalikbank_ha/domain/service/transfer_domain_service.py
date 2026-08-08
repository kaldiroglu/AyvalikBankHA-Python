from decimal import Decimal

from ..model import CustomerTier, Money
from ..model.rule_violation import (
    TransactionLimitExceededException,
)


class TransferDomainService:
    def calculate_fee(
        self,
        amount: Money,
        same_customer: bool,
        fee_percent: Decimal,
        source_tier: CustomerTier,
    ) -> Money:
        if same_customer:
            return Money.zero(amount.currency)
        scaled_percent = fee_percent * source_tier.fee_multiplier()
        fee = (amount.amount * scaled_percent / Decimal(100)).quantize(Decimal("0.01"))
        return Money(fee, amount.currency)

    def require_transfer_within_limit(self, amount: Money, tier: CustomerTier) -> None:
        cap = tier.max_per_transfer()
        if cap is not None and amount.amount > cap:
            raise TransactionLimitExceededException(
                f"Transfer amount {amount.amount} exceeds {tier.value} tier limit of {cap}"
            )

    def require_withdrawal_within_limit(self, amount: Money, tier: CustomerTier) -> None:
        cap = tier.max_per_withdrawal()
        if cap is not None and amount.amount > cap:
            raise TransactionLimitExceededException(
                f"Withdrawal amount {amount.amount} exceeds {tier.value} tier limit of {cap}"
            )
