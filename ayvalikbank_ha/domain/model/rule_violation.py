"""The account domain's refusal vocabulary.

Before this existed the domain raised ``PermissionError`` from 23 places, all meaning different
things. ``PermissionError`` is an ``OSError`` subclass whose documented meaning is *filesystem
permission denied* — so "insufficient funds" was being reported with the same type the interpreter
raises when a file cannot be opened, and a genuine OS permission failure inside a service method
would have been translated into a banking business error.

The four subtypes below give each refusal a name, so the application layer can translate by type
rather than by guessing from context.

**Honest limitation.** Python has no sealed types, so nothing checks that the translation covers
every subtype — the guarantee AyvalikBankHA-JAVA gets from ``sealed`` and an exhaustive ``switch``,
and that AyvalikBankHA-NET approximates with a throwing discard arm, is not available here. The
translator raises on an unknown subtype so a gap fails loudly at runtime, which is the strongest
guarantee this language offers.

Mirrors AyvalikBankHA-JAVA Refactorings.md entry 4.
"""

from __future__ import annotations


class AccountRuleViolation(Exception):
    """Base type for every way the account domain can refuse an operation."""


class AccountNotActiveException(AccountRuleViolation):
    """The account's lifecycle state forbids the operation — frozen, closed, or an invalid transition."""


class InsufficientBalanceException(AccountRuleViolation):
    """The balance, plus any overdraft allowance, cannot cover the requested debit."""


class OperationNotPermittedException(AccountRuleViolation):
    """The account product's own rules forbid the operation (locked principal, not matured, already accrued)."""


class TransactionLimitExceededException(AccountRuleViolation):
    """The amount exceeds the per-transaction cap carried by the customer's tier."""
