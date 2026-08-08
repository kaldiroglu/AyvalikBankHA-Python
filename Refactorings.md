# Refactorings

Claude Opus 5 (1M context) — created 2026-08-08

A log of significant refactorings applied to Ayvalık Bank HA-Python. Each entry records what the code
looked like before, what it looks like after, and — most importantly — *why* the change was worth
making.

For further enquiry please contact Akin Kaldiroglu at akin@kaldiroglu.dev

**Relationship to the other implementations.** This repository is one of six: hexagonal and layered,
in Java, .NET and Python. The refactorings below were designed in `AyvalikBankHA-JAVA` and ported
here, and each entry cross-references the Java write-up.

**Read the limitations honestly.** Python could not reproduce two of these guarantees. Where the
language cannot enforce something, the entry says so plainly and the test suite demonstrates the
hole rather than implying a safety that is not there. All six implementations are held to one HTTP
contract by `AyvalikBankContractTests`.

---

## Entry 1 — Ownership authorization: a rule that could not be said

**Baseline:** `105ec5c` · **Commit:** `07be7fa`

### The symptom

Any authenticated customer could operate on any other customer's data:

- `PUT /api/customers/{customer_id}/password` took its target from the path, gated only on the
  CUSTOMER role. **Any customer could set any other customer's password, then log in as them.**
- Given an account id, any customer could deposit to it, withdraw from it, transfer out of it, and
  read its balance and full transaction history.
- The three account-opening endpoints took `owner_id` as a query parameter with no check.

### The tell

Unlike the Java and .NET implementations — where an `UnauthorizedAccessException` sat mapped to 403
and never thrown — **this repository had no such exception and no 403 mapping at all**. There was not
even a dead handler to hint that the rule was meant to exist. Both were added.

### The root cause

Not one customer-facing `Command` carried the caller, so "the caller must own this account" was not
merely unenforced — it was **inexpressible**.

### What made this port trivial

`require_customer` **already returned the authenticated `Customer`**, and every controller threw it
away:

```python
_=Depends(require_customer),      # the caller, discarded
```

Java needed a new principal type and a test fixture. Here the identity was already computed on every
request and deliberately dropped on the floor.

> In four of the six implementations the caller's identity was already available and unused. The
> vulnerability was never about missing information — the rule had no place to live at the point of
> decision.

### Three enforcement shapes

| Situation | Technique |
|---|---|
| The resource *is* the caller's | **Delete the parameter** — `owner_id` is gone; the caller is the owner |
| The path names a customer | **Require self** — path id must equal the caller |
| The path names an account | **Require ownership** — load, compare `owner_id` |

The password check runs **before** the repository lookup, so a caller cannot learn which customer ids
exist by distinguishing 404 from 403.

### The transfer asymmetry

The caller must own the **source**. The target is deliberately unchecked — sending money to other
people is the entire product, and a test pins that so the obvious-looking hardening fails loudly.

---

## Entry 2 — Optimistic locking

**Baseline:** `07be7fa` · **Commit:** `1d478ba`

### The symptom

Two concurrent withdrawals of 50 from a balance of 100 both read 100, both wrote 50. The balance
ended at **50** where it should be **0**, with **both** transaction rows written — money created
from nothing, ledger contradicting the account.

### Why this port was the easy one

`AccountPersistenceAdapter.save` already loaded through `session.get`, which populates the identity
map, then mutated that instance. So `version_id_col` alone closed the hole — no restructuring.

Compare: `AyvalikBankHA-JAVA` rebuilt a **detached** entity on every save and had to change its write
path; `AyvalikBankHA-NET` read with `AsNoTracking()` and had to change its **read** path, or its
token would have incremented forever while catching nothing.

> **An ORM can only protect a row you actually loaded.** Three implementations, three different
> answers to whether that was already true.

### A portability detail worth knowing

**SQLAlchemy's `version_id_col` starts at 1; Hibernate's `@Version` and EF's token start at 0.** The
tests assert the real value in each implementation rather than a shared assumption.

### The test needs no threads

Two sessions committing in a fixed order reproduce the bug deterministically. **A lost update is a
stale-read problem, not a timing problem.** `StaleDataError` maps to **409 Conflict** with a fixed
message rather than SQLAlchemy's, which names the table and key.

---

## Entry 3 — Speaking the same HTTP contract as the others

**Baseline:** `1d478ba` · **Commit:** `0e0d302`

`AyvalikBankContractTests` is a black-box HTTP suite run against all six implementations. Its first
run against this repository failed 11 of 29 cases. **Not one was a flaw in the suite.**

| | Java / .NET | Python (before) |
|---|---|---|
| Request fields | `targetAccountId`, `feePercent`, `newPassword` | `target_account_id`, `fee_percent`, `new_password` |
| Validation rejection | 400 | 422 (FastAPI default) |

**A client written against the Java API could not talk to this one at all** — every request carrying
a multi-word field was rejected before reaching any business logic.

DTOs now derive from a `_CamelModel` base whose alias generator bridges snake_case Python attributes
to camelCase JSON, and a `RequestValidationError` handler returns 400.

### The second-order effect

`test_cannot_change_another_customers_password` returned **422, not 403** — Pydantic rejected the
field name before the ownership check ran. The security fix from entry 1 was correct; the validation
layer was shadowing it. **A per-repository test could never have shown this, because each repository
agreed with itself.**

---

## Entry 4 — A refusal vocabulary: `PermissionError` is not a banking concept

**Baseline:** `5c0f1bb` · **Commit:** `66c561e`

### The symptom

The domain raised `PermissionError` from **23** places, all meaning different things, and the
application layer recovered the meaning by matching on the message:

```python
if msg.startswith("Insufficient"): ...
if "frozen" in msg.lower() or "closed" in msg.lower(): ...
```

**Rewording a domain message silently changed the HTTP status.**

Worse, `PermissionError` is an `OSError` subclass whose documented meaning is *filesystem permission
denied*. "Insufficient funds" carried the same type the interpreter raises when a file cannot be
opened — and a genuine OS permission failure inside a service method would have surfaced as a banking
business error.

### The change

`AccountRuleViolation` with four subtypes and a type-based translator. All 23 sites retyped; **zero
message matching remains**.

### Why this migration could not be incremental

In `AyvalikBankHA-JAVA` the new base extended `IllegalStateException`, so all 25 existing assertions
kept passing — because that type was **correct but too coarse**.

Here the old base was `PermissionError`, which was **wrong**. Inheriting from it to keep the tests
green would have preserved exactly the confusion being removed. So 22 domain assertions had to move.

> The trick that made Java's migration free does not transfer. You cannot inherit your way out of a
> semantic error — only out of an imprecise one.

### What Python cannot do

Java seals the hierarchy and the compiler proves the translation total. C# approximates with a
throwing discard arm. Python has neither: the translator is an `isinstance` chain ending in a
`raise`, so a gap fails loudly at runtime. That is the strongest guarantee available here, and it is
the weakest of the three.

---

## Entry 5 — TransactionAmount, and a guarantee Python cannot give

**Baseline:** `66c561e` · **Commit:** `01043d9`

### The problem

`Money` deliberately allows negatives — a checking account balance goes negative under overdraft — so
it cannot enforce positivity, and every money-moving method re-asserted the rule by hand. One type
was serving both *balance* (signed position) and *amount* (unsigned magnitude), and could enforce
neither.

### The change

`TransactionAmount` wraps `Money` and validates once. **Zero is rejected as well as negative** —
direction is carried by which operation was called, and a zero-value transfer would write two ledger
rows recording no movement of money.

### The honest limitation

| | Can an invalid amount exist? |
|---|---|
| **Java** | No. `record` + compact constructor. |
| **.NET** | No — but only because it is a `class`; a `readonly record struct` would allow `default(T)`. |
| **Python** | **Yes.** `object.__new__` bypasses `__post_init__` entirely. |

Rather than paper over this, `test_the_guarantee_is_a_convention_not_an_invariant` **smuggles a
negative amount past validation and asserts it worked**, with a docstring explaining why the test
exists.

> A reader who assumes the Java guarantee holds here gets corrected by the test suite instead of by
> a production incident. Three files that look identical and are not would be worse than three that
> state their differences.

What this buys in Python is call-site clarity and one place the rule lives — a strong convention, not
an enforced invariant.

---

## Entry 6 — Actor-shaped ports

**Baseline:** `01043d9` · **Commit:** `113d684`

### The symptom

`use_cases.py` held **20 single-method Protocols**. The account controller carried nine
dependencies, the admin controller ten.

Worse, the controllers depended on the **concrete** `AccountApplicationService`, importing the
Protocols only for their nested `Command` types. The ports were command containers, not a boundary.

### The principle

Cockburn: **a port is one conversation with one kind of outside actor.** Two actors × three subjects
gives five ports.

Twenty single-method interfaces segregated nothing — a customer-facing controller uses all nine
customer-facing methods. Where Interface Segregation genuinely bites is the **actor boundary**: the
admin controller must not depend on `deposit` and `withdraw`. Controllers now type-hint the port.

### What the contract suite caught that 102 unit tests did not

```python
service: Annotated[IAccountAdministrationPort | IBankSettingsPort, Depends(get_account_service)]
```

FastAPI cannot resolve a **union of Protocols** as a dependency — it read `service` as a missing
request field, and **every admin account endpoint returned 400**. All 102 unit tests passed
throughout, because they construct the service directly and never exercise dependency resolution.

> Three separate defects in this codebase have now lived in the wiring between framework and
> application, invisible to tests that call the code directly. That is the argument for a suite that
> speaks only HTTP.

---

## Deliberate non-goals

- **`CustomerJpaEntity` has the same lost-update exposure** as accounts. The same fix applies; left
  out to keep entry 2 reviewable.
- **No retry-on-conflict.** A 409 tells the client to retry; automatic retry is a separate design.
- **`change_password` does not verify the current password.** Defensible under HTTP Basic; not once
  sessions arrive.
- **No controller tests.** The web layer is covered by `AyvalikBankContractTests`, which needs a
  running instance — so nothing here catches a wiring defect offline.

## Discussion questions

1. Entry 5 ships a test that proves the type's guarantee can be bypassed. Argue for and against
   keeping it.
2. Entry 4 says you cannot inherit your way out of a semantic error. What other refactorings does
   that rule change?
3. Entries 3 and 6 were both found only over HTTP. What would a per-repository test have to look
   like to catch either?
