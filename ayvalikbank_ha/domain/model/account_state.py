from __future__ import annotations

from abc import ABC, abstractmethod

from .account_status import AccountStatus


class AccountState(ABC):
    """State pattern. Each state owns its valid transitions and operability check.
    Stateless singletons — instantiate via the module-level constants below."""

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

    @property
    def is_terminal(self) -> bool:
        return False

    @staticmethod
    def of(status: AccountStatus) -> "AccountState":
        return _BY_STATUS[status]


class ActiveState(AccountState):
    @property
    def status(self) -> AccountStatus:
        return AccountStatus.ACTIVE

    def freeze(self) -> AccountState:
        return FROZEN

    def unfreeze(self) -> AccountState:
        raise PermissionError("Account is not frozen")

    def close(self) -> AccountState:
        return CLOSED

    def require_operable(self) -> None:
        return None


class FrozenState(AccountState):
    @property
    def status(self) -> AccountStatus:
        return AccountStatus.FROZEN

    def freeze(self) -> AccountState:
        raise PermissionError("Account is already frozen")

    def unfreeze(self) -> AccountState:
        return ACTIVE

    def close(self) -> AccountState:
        return CLOSED

    def require_operable(self) -> None:
        raise PermissionError("Account is frozen")


class ClosedState(AccountState):
    @property
    def status(self) -> AccountStatus:
        return AccountStatus.CLOSED

    def freeze(self) -> AccountState:
        raise PermissionError("Cannot freeze a closed account")

    def unfreeze(self) -> AccountState:
        raise PermissionError("Cannot unfreeze a closed account")

    def close(self) -> AccountState:
        raise PermissionError("Account is already closed")

    def require_operable(self) -> None:
        raise PermissionError("Account is closed")

    @property
    def is_terminal(self) -> bool:
        return True


ACTIVE: AccountState = ActiveState()
FROZEN: AccountState = FrozenState()
CLOSED: AccountState = ClosedState()

_BY_STATUS: dict[AccountStatus, AccountState] = {
    AccountStatus.ACTIVE: ACTIVE,
    AccountStatus.FROZEN: FROZEN,
    AccountStatus.CLOSED: CLOSED,
}
