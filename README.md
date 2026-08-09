# Ayvalık Bank HA-Python

A banking application built as a learning project to demonstrate **Hexagonal Architecture (Ports & Adapters)** in **Python 3.12+ / FastAPI / SQLAlchemy 2.0 (async)**. Python counterpart to `AyvalikBankHA-JAVA` (Java/Spring Boot) and `AyvalikBankHA-NET` (.NET).

For further enquiry please contact Akin Kaldiroglu at akin@kaldiroglu.dev

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
.venv/bin/uvicorn ayvalikbank_ha.main:app --port 8000 --reload
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

## Ports across the six repos

The six Ayvalık Bank implementations are meant to be compared side by side, so every one
takes its own application port and its own PostgreSQL port. All six can run at once.

| Repo | App | PostgreSQL | Database | Port pinned by |
|---|---|---|---|---|
| `AyvalikBankHA-JAVA` | **8080** | **5437** | `ayvalikbank_ha_java` | Spring Boot's default — nothing to configure |
| `AyvalikBankLA-JAVA` | **8081** | **5438** | `ayvalikbank_la_java` | `server.port=8081` in `application.properties` |
| `AyvalikBankHA-NET` | **5080** | **5434** | `ayvalikbank_ha_net` | `--urls http://localhost:5080`, **required** — there is no `launchSettings.json`, and without the flag Kestrel binds 5000 |
| `AyvalikBankLA-NET` | **5050** | **5433** | `ayvalikbank_la_net` | `AyvalikBankLA.Api/Properties/launchSettings.json` |
| `AyvalikBankHA-Python` | **8000** | **5436** | `ayvalikbank_ha_python` | `--port 8000` on the uvicorn command line |
| `AyvalikBankLA-Python` | **8001** | **5435** | `ayvalikbank_la_python` | `--port 8001` on the uvicorn command line |

**5432 is deliberately left free** for a native PostgreSQL install (Postgres.app, Homebrew).
A container bound to it collides, and — worse — an application pointed at it connects to the
native server instead of its own container with no error to say so.

The two Python repos are the fragile pair: uvicorn takes its port as a launch argument and
has no configuration file to default it in, so **omitting `--port` gives both 8000** and the
second one to start fails to bind. The documented commands always pass it explicitly. Spring
Boot and ASP.NET pin theirs in files, so those hold however the app is launched.
