# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**Ayvalık Bank HA-Python** — Python 3.12+ / FastAPI / SQLAlchemy 2.0 (async) port of `AyvalikBankHA-JAVA` (the Java/Spring Boot hexagonal project) and `AyvalikBankHA-NET` (the .NET port). Same use cases, same architectural discipline.

## Commands

```bash
docker compose up -d                                     # Postgres on port 5436
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q                                      # all 66 tests
.venv/bin/uvicorn ayvalikbank_ha.main:app --reload
```

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
