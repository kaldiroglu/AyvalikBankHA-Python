# Enhancement Walkthrough — Daily Withdrawal Limits

A teaching example: add **per-account, per-calendar-day cumulative withdrawal limits** to the project, then study where the change lands.

This file describes the feature in this codebase (Python 3.12+ / FastAPI / SQLAlchemy 2.0 async / hexagonal). Sibling files in `AyvalikBankHA1`, `AyvalikBankLA1`, `AyvalikBankHA-NET`, `AyvalikBankLA-NET`, `AyvalikBankLA-Python` describe the same feature in their respective stacks so the impact can be compared side by side.

---

## The Feature

- Each `Account` carries a nullable `daily_withdrawal_limit: Money | None`. None = use a tier-derived default.
- Cumulative withdrawals (direct withdraw + the debit side of transfers) on a single UTC calendar day must not exceed that limit.
- Admin can set/clear the limit per account: `PUT /api/admin/accounts/{id}/daily-limit`.
- Reset at UTC midnight.
- A separate, additive constraint — the existing per-transaction tier caps still apply.

---

## Why this feature is good for teaching

It crosses every layer: model, persistence, business rule, API, validation. It introduces **state that lives across transactions** ("today's running total"), which is the interesting persistence question. And it sits at the intersection of `Customer`, `Account`, and `Transaction` — three aggregates — which forces an architectural decision.

---

## Impact on this project — Python 3.12+ / FastAPI / SQLAlchemy 2.0 (async) / Hexagonal

### Files to add or modify

| # | Layer | Path | Change |
|---|---|---|---|
| 1 | Domain model | `domain/model/account.py` (and the three subtypes) | Add `_daily_withdrawal_limit: Money | None` on the abstract base + ctor parameter (default `None`) + read-only property |
| 2 | Domain service | `domain/service/withdrawal_policy_service.py` *(new)* | Pure class with `require_within_daily_limit(account, withdrawn_so_far: Money, requested: Money)` — instantiated in `main.py` (no decorators) |
| 3 | Domain port (out) | `domain/port/out/repository_ports.py` | Add `class IDailyWithdrawalQueryPort(Protocol): async def sum_withdrawals(self, account_id: UUID, utc_day: date) -> Money: ...` |
| 4 | Domain port (in) | `domain/port/in_/use_cases.py` | Add `class ISetAccountDailyLimitUseCase(Protocol)` with nested `Command` dataclass |
| 5 | Application | `application/service/account_application_service.py` | Constructor gains `withdrawal_policy: WithdrawalPolicyService` and `daily_query: IDailyWithdrawalQueryPort`. In `withdraw` and `transfer`, two new lines: query port → policy → wrap any thrown exception as `LimitExceededException` (already mapped to 422). Implement the new use case. Use-case Protocols unchanged. |
| 6 | Adapter (out) | `adapter/out/persistence/entity/jpa_entities.py` | Add `daily_withdrawal_limit: Mapped[Decimal | None] = mapped_column(Numeric(19, 2), nullable=True)` |
| 7 | Adapter (out) | `adapter/out/persistence/adapter/daily_withdrawal_query_adapter.py` *(new)* | Implements the port with a `select(func.coalesce(func.sum(TransactionJpaEntity.amount), 0))` filtered by `account_id`, `type == 'WITHDRAWAL'`, and the day-boundary `timestamp` range |
| 8 | Adapter (out) | `adapter/out/persistence/mapper/mappers.py` | Copy the new field both ways (in `to_domain` and `to_jpa` for each subtype) |
| 9 | Adapter (in) | `adapter/in_/web/admin_controller.py` | New endpoint + Pydantic `SetDailyLimitRequest(BaseModel)` |
| 10 | Composition | `main.py` | Build the new adapter inside `_account_service()` provider (alongside the other repos), pass it into `AccountApplicationService(...)`. Instantiate `WithdrawalPolicyService` once at module scope. |
| 11 | Tests | `tests/test_withdrawal_policy_service.py` *(new)* | 4–5 pure pytest tests using hand-built `Money` values — no SQLAlchemy, no FastAPI |
| 12 | Tests | `tests/test_account_application_service.py` *(new, optional)* | Mock the new port via a stub class to exercise the application service |

### Tech-stack-specific notes (Python)

- **`Money` value object** — already a frozen dataclass. Adding a `Money | None` field is trivial; the abstract `Account` ctor takes one extra parameter that subtypes pass through.
- **`typing.Protocol` for the new port** — no inheritance required; the adapter just has to match the shape. The PEP 544 structural-typing seam is doing real work here.
- **SQLAlchemy 2.0 async aggregate query**:
  ```python
  from sqlalchemy import func, select
  start = datetime.combine(utc_day, time.min, tzinfo=timezone.utc)
  end = start + timedelta(days=1)
  result = await self._session.execute(
      select(func.coalesce(func.sum(TransactionJpaEntity.amount), 0))
      .where(TransactionJpaEntity.account_id == account_id)
      .where(TransactionJpaEntity.type == TransactionType.WITHDRAWAL.value)
      .where(TransactionJpaEntity.timestamp >= start, TransactionJpaEntity.timestamp < end)
  )
  total = result.scalar_one()
  return Money(Decimal(total), currency)
  ```
- **Async session lifecycle** — the new query runs in the same per-request session that `withdraw` already uses; commit/rollback boundary is unchanged.
- **`DateOnly` doesn't exist in Python** — use `datetime.date` for the day, `datetime` (with tz) for the boundary timestamps.
- **DI** — the `AccountApplicationService` constructor signature grows by one parameter; `main.py`'s `_account_service()` provider gets one extra line.
- **Exception mapping** — `register_exception_handlers` already maps `LimitExceededException → 422`. If you want a more specific `DailyLimitExceededException`, subclass it so the existing handler still matches.
- **Schema isolation** — `domain/` stays free of SQLAlchemy; persistence layer adds the column on its own JpaEntity.

### Test impact

- **`tests/test_withdrawal_policy_service.py`**: pure pytest, no fixtures, no async — exercises the rule with hand-built `Money` values. Sub-millisecond.
- **`tests/test_account_application_service.py`** (optional): the new `IDailyWithdrawalQueryPort` is a `Protocol`, so a 5-line stub class implementing `sum_withdrawals` is enough to drive the application service without a database. This is the kind of test that's *easy in HA, awkward in LA*.
- The existing 66 unit tests are unaffected (the `Account` ctor change is backward-compatible if `daily_withdrawal_limit` defaults to `None`).

---

## Lesson Plan (apply to all six projects)

1. **Show both diffs side by side.** Count files; count *lines where the actual rule lives*.
2. **Change the rule** — "reset at customer's local midnight, not UTC." In HA you change one method on `WithdrawalPolicyService` + one query in the adapter. In LA you edit a long `withdraw` method that's already doing five other things.
3. **Add a second consumer** — `GET /api/accounts/{id}/today-summary` showing withdrawn-so-far + remaining-limit. In HA: one controller method calling the existing port + policy. In LA: copy the SQL `SUM` + comparison into a new service method.

The moral: **architecture is a bet about which kinds of change are likely.** HA bets on rules changing and being reused — it pays a structural tax up front. LA bets on rules being stable and local — it pays an entanglement tax later.
