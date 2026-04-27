from decimal import Decimal

import pytest

from ayvalikbank_ha.domain.model import Currency, CustomerTier, Money
from ayvalikbank_ha.domain.service import TransferDomainService


@pytest.fixture
def service() -> TransferDomainService:
    return TransferDomainService()


def test_same_customer_is_free(service):
    assert (
        service.calculate_fee(
            Money(Decimal("200"), Currency.USD), True, Decimal("1.0"), CustomerTier.STANDARD
        ).amount
        == Decimal("0")
    )


def test_standard_tier_applies_full_percent(service):
    assert (
        service.calculate_fee(
            Money(Decimal("200"), Currency.USD), False, Decimal("1.0"), CustomerTier.STANDARD
        ).amount
        == Decimal("2.00")
    )


def test_premium_tier_applies_half_percent(service):
    assert (
        service.calculate_fee(
            Money(Decimal("200"), Currency.USD), False, Decimal("1.0"), CustomerTier.PREMIUM
        ).amount
        == Decimal("1.00")
    )


def test_private_tier_is_free(service):
    assert (
        service.calculate_fee(
            Money(Decimal("10000"), Currency.USD), False, Decimal("1.0"), CustomerTier.PRIVATE
        ).amount
        == Decimal("0.00")
    )


def test_standard_transfer_over_cap_throws(service):
    with pytest.raises(PermissionError, match="5000"):
        service.require_transfer_within_limit(
            Money(Decimal("5001"), Currency.USD), CustomerTier.STANDARD
        )


def test_standard_transfer_at_cap_passes(service):
    service.require_transfer_within_limit(
        Money(Decimal("5000"), Currency.USD), CustomerTier.STANDARD
    )


def test_premium_transfer_over_cap_throws(service):
    with pytest.raises(PermissionError, match="50000"):
        service.require_transfer_within_limit(
            Money(Decimal("50001"), Currency.USD), CustomerTier.PREMIUM
        )


def test_private_transfer_has_no_cap(service):
    service.require_transfer_within_limit(
        Money(Decimal("10000000"), Currency.USD), CustomerTier.PRIVATE
    )


def test_standard_withdrawal_over_cap_throws(service):
    with pytest.raises(PermissionError, match="5000"):
        service.require_withdrawal_within_limit(
            Money(Decimal("5001"), Currency.USD), CustomerTier.STANDARD
        )


def test_private_withdrawal_has_no_cap(service):
    service.require_withdrawal_within_limit(
        Money(Decimal("10000000"), Currency.USD), CustomerTier.PRIVATE
    )
