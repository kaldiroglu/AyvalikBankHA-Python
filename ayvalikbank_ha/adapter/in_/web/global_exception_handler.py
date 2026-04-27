from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ....application.exception import (
    AccountNotOperableException,
    InsufficientFundsException,
    InvalidAccountOperationException,
    InvalidCredentialsException,
    LimitExceededException,
    NotFoundException,
    PasswordReuseException,
    PasswordValidationException,
)


def _problem(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"type": "about:blank", "title": title, "status": status, "detail": detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundException)
    async def _not_found(req: Request, exc: NotFoundException) -> JSONResponse:
        return _problem(404, "Not Found", str(exc))

    @app.exception_handler(InvalidCredentialsException)
    async def _bad_creds(req: Request, exc: InvalidCredentialsException) -> JSONResponse:
        return _problem(401, "Invalid Credentials", str(exc))

    @app.exception_handler(PasswordValidationException)
    async def _bad_password(req: Request, exc: PasswordValidationException) -> JSONResponse:
        return _problem(422, "Password Validation Failed", str(exc))

    @app.exception_handler(PasswordReuseException)
    async def _password_reuse(req: Request, exc: PasswordReuseException) -> JSONResponse:
        return _problem(422, "Password Reused", str(exc))

    @app.exception_handler(InsufficientFundsException)
    async def _funds(req: Request, exc: InsufficientFundsException) -> JSONResponse:
        return _problem(422, "Insufficient Funds", str(exc))

    @app.exception_handler(AccountNotOperableException)
    async def _not_operable(req: Request, exc: AccountNotOperableException) -> JSONResponse:
        return _problem(422, "Account Not Operable", str(exc))

    @app.exception_handler(InvalidAccountOperationException)
    async def _invalid_op(req: Request, exc: InvalidAccountOperationException) -> JSONResponse:
        return _problem(422, "Invalid Account Operation", str(exc))

    @app.exception_handler(LimitExceededException)
    async def _limit(req: Request, exc: LimitExceededException) -> JSONResponse:
        return _problem(422, "Limit Exceeded", str(exc))

    @app.exception_handler(ValueError)
    async def _value(req: Request, exc: ValueError) -> JSONResponse:
        return _problem(400, "Bad Request", str(exc))
