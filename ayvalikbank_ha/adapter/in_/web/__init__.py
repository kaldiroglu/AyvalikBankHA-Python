from .account_controller import router as account_router
from .admin_controller import router as admin_router
from .customer_controller import router as customer_router
from .global_exception_handler import register_exception_handlers

__all__ = [
    "account_router",
    "admin_router",
    "customer_router",
    "register_exception_handlers",
]
