from decimal import Decimal

from ayvalikbank_ha.domain.model import Customer, CustomerTier


def test_standard_tier_has_full_fee_and_five_thousand_caps():
    assert CustomerTier.STANDARD.fee_multiplier() == Decimal("1.00")
    assert CustomerTier.STANDARD.max_per_transfer() == Decimal("5000")
    assert CustomerTier.STANDARD.max_per_withdrawal() == Decimal("5000")


def test_premium_tier_has_half_fee_and_higher_caps():
    assert CustomerTier.PREMIUM.fee_multiplier() == Decimal("0.50")
    assert CustomerTier.PREMIUM.max_per_transfer() == Decimal("50000")
    assert CustomerTier.PREMIUM.max_per_withdrawal() == Decimal("25000")


def test_private_tier_has_no_fee_and_no_caps():
    assert CustomerTier.PRIVATE.fee_multiplier() == Decimal("0.00")
    assert CustomerTier.PRIVATE.max_per_transfer() is None
    assert CustomerTier.PRIVATE.max_per_withdrawal() is None


def test_new_customer_defaults_to_standard():
    c = Customer.create("Alice", "alice@example.com", "hash")
    assert c.tier is CustomerTier.STANDARD


def test_change_tier_updates_customer():
    c = Customer.create("Alice", "alice@example.com", "hash")
    c.change_tier(CustomerTier.PRIVATE)
    assert c.tier is CustomerTier.PRIVATE
