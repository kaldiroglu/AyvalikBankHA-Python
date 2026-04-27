# Tests — Ayvalık Bank HA-Python

**Stack:** pytest · pytest-asyncio
**Total:** 66 tests · 100% passing
**Run:** `.venv/bin/pytest -q`

All tests are unit tests on the domain and the domain service layer. Application and adapter layers are exercised through the domain. (Integration tests with `httpx.AsyncClient` against the FastAPI app + SQLite are a planned extension.)

---

## Summary by Test File

| File | Tests | Focus |
|---|---:|---|
| `test_money.py` | 4 | Value object: zero, add, currency-mismatch guard, comparison |
| `test_password_validation_service.py` | 5 | Length, digit, uppercase, special-char rules |
| `test_account.py` | 8 | Cross-cutting on the abstract `Account` API (via `CheckingAccount.open`) |
| `test_checking_account.py` | 7 | Overdraft happy path + cap rejection + currency / negative-limit guards |
| `test_savings_account.py` | 7 | `accrue_interest` math, double-accrual rejection, frozen vs. closed behavior |
| `test_time_deposit_account.py` | 9 | Lock invariants, `mature(today)` credit, double-mature rejection, invalid construction |
| `test_account_state.py` | 11 | All `AccountState` transitions and operability checks |
| `test_customer_tier.py` | 5 | `CustomerTier` policy data + `Customer.change_tier` |
| `test_transfer_domain_service.py` | 10 | Tier-aware `calculate_fee`; per-transaction `require_*_within_limit` |

---

## Coverage by Domain Concern

### `Money` (value object)
- `zero_is_zero`, `adds_same_currency`, `rejects_add_different_currency`, `gte_works_within_same_currency`

### `PasswordValidationService`
- `accepts_valid`, `rejects_short`, `rejects_no_digit`, `rejects_no_upper`, `rejects_no_special`

### `Account` (abstract base, via `CheckingAccount.open`)
- `opens_at_zero_and_active`
- `deposit_raises_balance_and_returns_transaction`, `withdraw_decreases_balance`
- `withdrawing_more_than_balance_throws`, `deposit_in_wrong_currency_throws`
- `freeze_blocks_deposit`, `close_is_terminal`
- `transfer_out_with_fee_deducts_total`

### `CheckingAccount`
- `opens_without_overdraft_by_default`, `opens_with_overdraft_limit`
- `withdraw_without_overdraft_rejects_overdraw`
- `withdraw_within_overdraft_allows_negative_balance`
- `withdraw_beyond_overdraft_throws`
- `overdraft_currency_must_match`, `negative_overdraft_rejected`

### `SavingsAccount`
- `opens_with_given_interest_rate`
- `negative_interest_rate_rejected`
- `withdraw_cannot_go_negative`
- `accrue_interest_adds_monthly_interest` — 12% annual / 12 = 1% monthly → `1000 → 1010`
- `accrue_interest_for_same_month_rejected`
- `accrue_interest_on_closed_rejected`
- `accrue_on_frozen_still_works`

### `TimeDepositAccount`
- `opens_with_principal_as_balance`
- `deposit_rejected`, `transfer_out_rejected`, `withdraw_before_maturity_rejected`
- `mature_before_maturity_date_rejected`
- `mature_credits_interest_and_allows_withdraw` — `10000 × 5% × 1y = 500` credit
- `mature_twice_rejected`
- `non_positive_principal_rejected`, `maturity_date_before_opened_on_rejected`

### `AccountState` (State pattern)
- `new_account_is_active`, `freeze_moves_to_frozen`, `unfreeze_moves_frozen_to_active`
- `freezing_frozen_throws`, `unfreezing_active_throws`
- `close_from_active_is_terminal`, `close_from_frozen_is_terminal`
- `closed_rejects_all_transitions`
- `frozen_blocks_deposit`, `frozen_blocks_withdraw`, `closed_blocks_deposit`

### `CustomerTier`
- `standard_tier_has_full_fee_and_five_thousand_caps`
- `premium_tier_has_half_fee_and_higher_caps`
- `private_tier_has_no_fee_and_no_caps`
- `new_customer_defaults_to_standard`, `change_tier_updates_customer`

### `TransferDomainService`
- `same_customer_is_free`
- `standard_tier_applies_full_percent`, `premium_tier_applies_half_percent`, `private_tier_is_free`
- `standard_transfer_over_cap_throws`, `standard_transfer_at_cap_passes`
- `premium_transfer_over_cap_throws`, `private_transfer_has_no_cap`
- `standard_withdrawal_over_cap_throws`, `private_withdrawal_has_no_cap`

---

## Known Gaps

- **No application service tests.** `CustomerApplicationService` / `AccountApplicationService` are exercised indirectly via the domain. Direct tests with mocked Protocol implementations would shore up the orchestration layer.
- **No HTTP/web tests.** Controllers and `register_exception_handlers` are not tested directly. `httpx.AsyncClient` against the FastAPI app + SQLite + `app.dependency_overrides` is a planned add.
- **No coverage tooling.** Adding `pytest --cov=ayvalikbank_ha` would mirror the Java sibling's JaCoCo report.

---

## How to Run

```bash
.venv/bin/pytest -q                                      # all tests
.venv/bin/pytest tests/test_checking_account.py          # single file
.venv/bin/pytest -k "accrue"                             # by keyword
.venv/bin/pytest -v                                      # verbose
```
