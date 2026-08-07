class NotFoundException(Exception):
    pass


class InvalidCredentialsException(Exception):
    pass


class PasswordValidationException(Exception):
    pass


class PasswordReuseException(Exception):
    pass


class InsufficientFundsException(Exception):
    pass


class AccountNotOperableException(Exception):
    pass


class InvalidAccountOperationException(Exception):
    pass


class LimitExceededException(Exception):
    pass


class UnauthorizedAccessException(Exception):
    """The caller may not act on this account or customer record.

    Mirrors AyvalikBankHA-JAVA Refactorings.md entry 3: any authenticated customer could
    previously operate on any account given its id, and set any other customer's password.
    """
    pass
