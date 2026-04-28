# Ayvalık Bank HA-Python

A banking application built as a learning project to demonstrate **Hexagonal Architecture (Ports & Adapters)** in **Python 3.12+ / FastAPI / SQLAlchemy 2.0 (async)**. Python counterpart to `AyvalikBankHA-JAVA` (Java/Spring Boot) and `AyvalikBankHA-NET` (.NET).

## Tech Stack

| Concern          | Technology                                    |
|------------------|----------------------------------------------|
| Runtime          | Python 3.12+                                 |
| Web              | FastAPI                                      |
| Persistence      | SQLAlchemy 2.0 (async) + asyncpg (PostgreSQL)|
| Auth             | FastAPI HTTP Basic                           |
| Validation       | Pydantic v2                                  |
| Testing          | pytest · pytest-asyncio                      |
| Password hashing | bcrypt                                       |
| Local infra      | Docker Compose (PostgreSQL on `5436`)        |

## Quick Start

```bash
docker compose up -d
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn ayvalikbank_ha.main:app --reload
```

Default admin: `admin@ayvalikbank.dev` / `Admin@123!` (seeded on first startup)

## Project Layout (hexagonal)

```
ayvalikbank_ha/
  domain/
    model/                 — sealed Account hierarchy, AccountState (State pattern),
                             Money, Customer, Transaction, enums
    service/               — TransferDomainService, PasswordValidationService
                             (zero framework imports)
    port/
      in_/use_cases.py     — 21 driving use-case Protocols
      out/                 — driven repository + hasher Protocols
  application/
    service/               — Account/CustomerApplicationService — implement
                             multiple use-case interfaces; orchestration only
    exception/             — typed application exceptions
  adapter/
    in_/web/               — controllers + DTOs + GlobalExceptionHandler
    out/persistence/       — JpaEntities + DbContext + Mappers + Adapters
    out/security/          — BcryptPasswordHasherAdapter
  config/                  — admin_seeder
  main.py                  — composition root: DI wiring lives here
tests/                     — pytest unit tests (66)
```

## Architectural notes

- **Sealed `Account` hierarchy** — `abstract class Account` + concrete `CheckingAccount / SavingsAccount / TimeDepositAccount` mirror the Java/.NET sealed hierarchies. Each subtype owns its own `deposit / withdraw / transfer_out`.
- **State pattern for status** — `AccountState` `ABC` + `ActiveState / FrozenState / ClosedState` module-level singletons. `Account.status` delegates to `state`; `CLOSED` is terminal.
- **Customer tiers** — `STANDARD / PREMIUM / PRIVATE` enum with policy methods: `fee_multiplier()` (1.0×/0.5×/0.0×) and per-transaction caps (5k/50k/unlimited transfer; 5k/25k/unlimited withdrawal).
- **Value object `Money`** — frozen dataclass with `Decimal` + `Currency`, plus arithmetic + same-currency guards.
- **Ports as `typing.Protocol`** — controllers depend on use-case protocols, services on repository protocols. Concrete implementations are wired in `main.py` via FastAPI's `dependency_overrides`.
- **Persistence adapter has its own `JpaEntities`** that map to/from domain entities; SQLAlchemy types never cross the persistence boundary.

## Endpoints

| Method | Path | Role |
|---|---|---|
| POST | `/api/admin/customers` | ADMIN |
| DELETE | `/api/admin/customers/{id}` | ADMIN |
| GET | `/api/admin/customers` | ADMIN |
| PUT | `/api/admin/settings/transfer-fee` | ADMIN |
| PUT | `/api/admin/accounts/{id}/freeze` | ADMIN |
| PUT | `/api/admin/accounts/{id}/unfreeze` | ADMIN |
| PUT | `/api/admin/accounts/{id}/close` | ADMIN |
| PUT | `/api/admin/customers/{id}/tier` | ADMIN |
| PUT | `/api/admin/accounts/{id}/accrue-interest` | ADMIN |
| PUT | `/api/admin/accounts/{id}/mature` | ADMIN |
| PUT | `/api/customers/{id}/password` | CUSTOMER |
| POST | `/api/accounts/checking?owner_id=` | CUSTOMER |
| POST | `/api/accounts/savings?owner_id=` | CUSTOMER |
| POST | `/api/accounts/time-deposit?owner_id=` | CUSTOMER |
| GET | `/api/customers/{id}/accounts` | CUSTOMER |
| GET | `/api/accounts/{id}/balance` | CUSTOMER |
| POST | `/api/accounts/{id}/deposit` | CUSTOMER |
| POST | `/api/accounts/{id}/withdraw` | CUSTOMER |
| POST | `/api/accounts/{id}/transfer` | CUSTOMER |
| GET | `/api/accounts/{id}/transactions` | CUSTOMER |

## Test coverage

66 unit tests (pytest), covering Money, PasswordValidation, the abstract Account API, CheckingAccount overdraft, SavingsAccount monthly accrual, TimeDepositAccount lock + maturation, AccountState transitions, CustomerTier policy, and TransferDomainService tier-aware fees + caps.
