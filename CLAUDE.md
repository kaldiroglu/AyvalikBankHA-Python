# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**Ayvalık Bank HA-Python** — Python 3.12+ / FastAPI / SQLAlchemy 2.0 (async) port of `AyvalikBankHA-JAVA` (the Java/Spring Boot hexagonal project) and `AyvalikBankHA-NET` (the .NET port). Same use cases, same architectural discipline.

## Cross-repository invariants

This repo is one of six (hexagonal + layered × Java/.NET/Python) that must stay **functionally
identical**. `AyvalikBankContractTests` is one black-box HTTP suite run against all six, and CI runs
it on every push. Before changing any endpoint, status code, field name or JSON shape, check whether
the change belongs in all six.

- Wire format is **camelCase**; validation failures are **400** (not FastAPI's default 422).
- Enums travel as **strings** (`"USD"`), never numbers.
- Refactoring write-ups live in `Refactorings.md`; the Java hexagonal repo is the reference.
- The suite is 29 tests; all six implementations currently pass 29/29.

## Commands

```bash
# Browsable API docs once the app is running: /docs
# Shared contract suite (from AyvalikBankContractTests):
#   BANK_BASE_URL=http://localhost:8000 pytest tests/

docker compose up -d                                     # Postgres on port 5436, database ayvalikbank_ha_python
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q                                      # all 102 tests
.venv/bin/uvicorn ayvalikbank_ha.main:app --port 8000 --reload

# Run without Docker (port 8000; LA-Python uses 8001)
DATABASE_URL="sqlite+aiosqlite:///./dev.db" .venv/bin/uvicorn ayvalikbank_ha.main:app --port 8000
```

## Environment gotchas

- **The venv hardcodes an absolute interpreter path** — moving the repo breaks it. Recreate with
  `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`.
- **`from __future__ import annotations` hides missing imports** until something resolves the
  annotation. A missing port import passed every test and CI, and only broke `/openapi.json`.
- **`.env` silently overrides `DEFAULT_DB_URL` in `main.py`.** `.env.example` was once wrong on
  user, password *and* port, and had been copied to a real `.env` — so the app connected to a native
  PostgreSQL on 5432 instead of its own container. Keep `.env.example` in step with
  `docker-compose.yml`; it exists to be copied.

## Ports and databases

This repo: app **8000**, PostgreSQL **5436**, database `ayvalikbank_ha_python`.

All six repos take distinct application and PostgreSQL ports so every one can run at the same
time; `README.md` carries the full table. **5432 is deliberately unused** — it is the default for
a native PostgreSQL (Postgres.app, Homebrew), and an application pointed at it connects to that
server instead of its own container, with no error to say so. Every compose service sets an
explicit `container_name`: without one Compose derives a name from the directory, and a container
can outlive the checkout that defined it while still holding its port.

## Architecture

Hexagonal (Ports & Adapters). Every dependency points inward — adapters depend on application, application depends on domain, domain depends on nothing.

```
domain/model/                — rich entities, value object Money, enums
domain/service/              — TransferDomainService, PasswordValidationService
domain/port/in_/             — driving Protocols (use cases)
domain/port/out/             — driven Protocols (repositories, hasher)

application/service/         — implement multiple use-case Protocols;
                               orchestration only (no business rules)
application/exception/       — typed application exceptions

adapter/in_/web/             — FastAPI controllers + Pydantic DTOs
adapter/out/persistence/     — SQLAlchemy entities + DbContext + Mappers + Adapters
adapter/out/security/        — BcryptPasswordHasherAdapter

config/                      — admin_seeder
main.py                      — composition root: DI wiring lives here
```

## Design Decisions (2026-08 hardening pass)

- **Ownership authorization**: every customer-facing command carries the caller's id, taken from the authenticated principal — never from a route or query parameter. Transfers check the **source only**; the target is deliberately unchecked. Opening an account takes no owner id: the caller is the owner. See `Refactorings.md`.
- **Optimistic locking**: accounts carry a version token. A conflict surfaces at commit and maps to HTTP 409.
- **Domain refusal vocabulary**: the domain refuses through `AccountRuleViolation` and four subtypes; the application layer translates by **type**, never by matching on the exception message.
- **`TransactionAmount` vs `Money`**: `Money` is signed (overdraft), so it cannot enforce positivity. `TransactionAmount` is strictly positive by construction and types the command surface. Balances, fees and recorded transaction amounts stay `Money` — zero is legal for all three.
- **Actor-shaped ports**: driving ports are grouped by *actor × subject*, not one per method. A port is one conversation with one kind of outside actor.

## Key Decisions (preserved from the Java sibling)

- **Domain has zero framework imports.** Pure Python only — no FastAPI, no SQLAlchemy, no Pydantic.
- **`Money` value object.** Frozen dataclass with `Decimal` + `Currency` + same-currency guards.
- **Sealed `Account` hierarchy.** Python lacks `sealed` keyword — discipline enforced via `abc.ABC` + a closed mapper switch over the three known subtypes (`CheckingAccount / SavingsAccount / TimeDepositAccount`).
- **State pattern.** `AccountState` `ABC` + `ActiveState / FrozenState / ClosedState` module-level singletons. `Account.status` delegates to `state`. CLOSED is terminal.
- **`CustomerTier` enum + policy methods.** `STANDARD / PREMIUM / PRIVATE` with `fee_multiplier()` (1.0×/0.5×/0.0×) and `max_per_transfer()` / `max_per_withdrawal()` (5k/50k/unlimited; 5k/25k/unlimited).
- **Ports as `typing.Protocol`.** PEP 544 structural typing — adapters need not declare inheritance, they just match the shape.
- **Persistence adapter has its own JPA-style entities** + mappers. SQLAlchemy types do not cross the persistence boundary.
- **Auth** — FastAPI `HTTPBasic`. Credentials checked against the `customers` table.
- **Composition root** — `main.py` via `app.dependency_overrides`. The controllers don't know about session lifecycle, engine, or hasher implementation.

## Default Admin

`admin@ayvalikbank.dev` / `Admin@123!` (seeded by `seed_admin` on first startup, with `tier = STANDARD`)
