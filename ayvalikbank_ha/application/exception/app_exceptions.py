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
