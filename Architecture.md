# Architecture — Ayvalık Bank HA-Python

A Python 3.12+ port of `AyvalikBankHA1`, organized as **Hexagonal Architecture (Ports & Adapters)** in idiomatic Python.

---

## Dependency Rule

```
adapter/in_/web ──▶ domain/port/in_ ◀── application/service ──▶ domain/port/out ◀── adapter/out/persistence
                          ▲                       │                                          │
                          │                       ▼                                          │
                          └────────────── domain/model + domain/service ◀──────────────────┘
```

- **Adapters** depend on **ports** (`typing.Protocol`).
- **Application services** orchestrate; they depend only on protocols and the domain.
- **Domain** has no FastAPI, no SQLAlchemy, no Pydantic.

---

## Project Layout

```
ayvalikbank_ha/
  domain/
    model/                     — Account hierarchy, AccountState (State pattern),
                                 Money, Customer, Transaction, enums
    service/                   — TransferDomainService, PasswordValidationService
    port/
      in_/use_cases.py         — 21 driving Protocols
      out/repository_ports.py  — driven repository + hasher Protocols
  application/
    service/                   — Customer/AccountApplicationService
                                 (each implements multiple use-case Protocols)
    exception/                 — typed application exceptions
  adapter/
    in_/web/                   — FastAPI controllers + Pydantic DTOs +
                                 GlobalExceptionHandler
    out/persistence/
      entity/                  — SQLAlchemy ORM entities (Jpa-style)
      db.py                    — async engine + sessionmaker
      mapper/                  — Domain ⇄ JpaEntity (subtype-aware switch)
      adapter/                 — implement domain Out ports
    out/security/              — BcryptPasswordHasherAdapter
  config/                      — admin_seeder
  main.py                      — composition root
tests/                         — pytest unit tests (66)
```

---

## Key Design Decisions

### Sealed `Account` hierarchy

Python lacks `sealed` keyword, but the discipline is preserved by:
- `abc.ABC` base class with abstract `deposit / withdraw / transfer_out`
- Three known subclasses: `CheckingAccount`, `SavingsAccount`, `TimeDepositAccount`
- The persistence mapper switches over `AccountType` exhaustively

```python
class Account(ABC):
    @abstractmethod
    def deposit(self, amount: Money) -> Transaction: ...
    @abstractmethod
    def withdraw(self, amount: Money) -> Transaction: ...
    @abstractmethod
    def transfer_out(self, ...) -> Transaction: ...

class CheckingAccount(Account): ...    # overdraft
class SavingsAccount(Account): ...      # accrue_interest
class TimeDepositAccount(Account): ...  # mature
```

### State pattern for `AccountStatus`

```python
class AccountState(ABC):
    @property
    @abstractmethod
    def status(self) -> AccountStatus: ...
    @abstractmethod
    def freeze(self) -> "AccountState": ...
    @abstractmethod
    def unfreeze(self) -> "AccountState": ...
    @abstractmethod
    def close(self) -> "AccountState": ...
    @abstractmethod
    def require_operable(self) -> None: ...

ACTIVE: AccountState = ActiveState()  # module-level singleton
FROZEN: AccountState = FrozenState()
CLOSED: AccountState = ClosedState()
```

Each state owns its valid transitions and operability check. `Account.status` delegates to `_state`.

### `CustomerTier` enum with policy methods

```python
class CustomerTier(str, Enum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    PRIVATE = "PRIVATE"

    def fee_multiplier(self) -> Decimal: ...
    def max_per_transfer(self) -> Decimal | None: ...
    def max_per_withdrawal(self) -> Decimal | None: ...
```

The lookup tables live in module-level dicts. Java embeds policy in enum methods; .NET uses extension methods; Python uses Enum methods.

### Ports as `typing.Protocol`

```python
class IDepositMoneyUseCase(Protocol):
    @dataclass(frozen=True)
    class Command:
        account_id: UUID
        amount: Money
    async def deposit(self, cmd: "IDepositMoneyUseCase.Command") -> Transaction: ...
```

PEP 544 **structural typing**: an adapter doesn't have to declare inheritance — it just has to match the shape. Application services in this project explicitly inherit from each Protocol they implement, but it's not required.

### Application services implement multiple use-case Protocols

```python
class AccountApplicationService(
    IOpenCheckingAccountUseCase,
    IOpenSavingsAccountUseCase,
    IDepositMoneyUseCase,
    IWithdrawMoneyUseCase,
    ITransferMoneyUseCase,
    # ... 15 use-case Protocols total
):
    ...
```

### Persistence adapter has its own JPA-style entities

`CustomerJpaEntity`, `AccountJpaEntity`, `TransactionJpaEntity`, `SettingsJpaEntity`, `PasswordHistoryJpaEntity` are SQLAlchemy `Base` subclasses inside the persistence adapter. **They never cross the boundary.** `AccountMapper.to_domain` switches on `AccountType` to construct the right subclass; `to_jpa` uses `isinstance` checks to write the right type-specific columns.

### Account table schema (single-table inheritance)

```
accounts
  id                uuid PK
  owner_id          uuid FK
  currency          text
  balance           numeric(19,2)
  status            text                 -- ACTIVE | FROZEN | CLOSED
  type              text                 -- CHECKING | SAVINGS | TIME_DEPOSIT
  overdraft_limit   numeric(19,2) NULL   -- CHECKING only
  interest_rate     numeric(19,4) NULL   -- SAVINGS, TIME_DEPOSIT
  last_accrual_date date          NULL   -- SAVINGS only
  principal         numeric(19,2) NULL   -- TIME_DEPOSIT only
  opened_on         date          NULL   -- TIME_DEPOSIT only
  maturity_date     date          NULL   -- TIME_DEPOSIT only
  matured           boolean       NULL   -- TIME_DEPOSIT only
```

### Cross-cutting

- **Authentication** — FastAPI `HTTPBasic` security dependency; credentials validated against the `customers` table.
- **Error handling** — `register_exception_handlers(app)` maps each typed exception to an RFC 7807-style `ProblemDetails` JSON body with the right status code (404, 401, 422).
- **Composition root** — `main.py` via FastAPI's `app.dependency_overrides`. Each request gets a fresh async session; commit/rollback at request boundary.

---

## Request Flow Examples

### `POST /api/accounts/checking?owner_id={id}`

```
HTTP request
  → AccountController.create_checking
      → AccountApplicationService.open_checking            (use-case Protocol)
        → ICustomerRepositoryPort.find_by_id               (out Protocol)
          → CustomerPersistenceAdapter
            → SQLAlchemy session.get
        → CheckingAccount.open(owner_id, currency, overdraft)
        → IAccountRepositoryPort.save
          → AccountPersistenceAdapter
            → AccountMapper.to_jpa  (isinstance branches)
            → session.flush
      ← AccountResponse.from_domain
HTTP 201 Created + JSON
```

### `POST /api/accounts/{id}/transfer` (cross-customer, with fee)

```
HTTP request
  → AccountController.transfer
      → AccountApplicationService.transfer
        → load source, target, source_owner, settings
        → TransferDomainService.require_transfer_within_limit (caps by tier)
        → TransferDomainService.calculate_fee(amount, same_customer, fee_pct, tier)
        → source.transfer_out(amount, fee, target.id) — domain method
        → target.transfer_in(amount, source.id)
        → save both, record transactions
HTTP 200 OK
```

---

## Tech Stack

| Concern          | Technology                                  |
|------------------|---------------------------------------------|
| Runtime          | Python 3.12+                                |
| Web              | FastAPI                                     |
| Persistence      | SQLAlchemy 2.0 (async) + asyncpg            |
| Auth             | FastAPI `HTTPBasic`                         |
| Validation       | Pydantic v2                                 |
| Testing          | pytest · pytest-asyncio                     |
| Password hashing | bcrypt                                      |
| Local infra      | Docker Compose (Postgres on `5436`)         |

---

## Comparison to the Java/.NET Siblings

| Aspect | Java HA1 | .NET HA-NET | Python HA-Python |
|---|---|---|---|
| Sealed account hierarchy | `sealed abstract class permits ...` | `abstract class` + `sealed class` | `abc.ABC` + closed mapper switch |
| State pattern | `sealed interface` + singletons | `abstract class` + sealed singletons | `abc.ABC` + module-level singletons |
| Money | `record Money(BigDecimal, Currency)` | `readonly record struct Money` | frozen dataclass with `Decimal` |
| Use-case ports | `interface CreateCustomerUseCase` | `interface ICreateCustomerUseCase` | `class ICreateCustomerUseCase(Protocol)` |
| Tier policy | enum methods | extension methods | enum methods |
| Persistence | JPA + Spring Data | EF Core + DbContext | SQLAlchemy + async session |
| DI | Spring `@Autowired` | constructor + `AddScoped<>` | FastAPI `Depends` + `dependency_overrides` |
| Auth | Spring Security HTTP Basic | `AuthenticationHandler<>` | FastAPI `HTTPBasic` |
| Error handler | `@ControllerAdvice` | `IExceptionHandler` | `@app.exception_handler(...)` |
