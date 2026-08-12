from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.schemas import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorResponse,
    ValidationIssue,
)
from backend.app.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    UpstreamInvalidResponseError,
    UpstreamUnavailableError,
)


def _error_response(error: DomainError, status_code: int) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(error, AuthenticationError) else None
    content = ErrorResponse(
        error=ErrorDetail(code=error.code, message=error.safe_message)
    ).model_dump()
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def handle_authentication_error(_: Request, error: AuthenticationError) -> JSONResponse:
    return _error_response(error, 401)


async def handle_conflict_error(_: Request, error: ConflictError) -> JSONResponse:
    return _error_response(error, 409)


async def handle_not_found_error(_: Request, error: NotFoundError) -> JSONResponse:
    return _error_response(error, 404)


async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
    return _error_response(error, 400)


async def handle_invalid_upstream_response(
    _: Request, error: UpstreamInvalidResponseError
) -> JSONResponse:
    return _error_response(error, 502)


async def handle_unavailable_upstream(_: Request, error: UpstreamUnavailableError) -> JSONResponse:
    return _error_response(error, 503)


async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
    content = ErrorResponse(
        error=ErrorDetail(code="internal_error", message="Internal server error")
    ).model_dump()
    return JSONResponse(status_code=500, content=content)


async def handle_validation_error(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    details = [
        ValidationIssue(loc=list(issue["loc"]), msg=issue["msg"], type=issue["type"])
        for issue in error.errors()
    ]
    content = ValidationErrorResponse(
        error=ErrorDetail(code="validation_error", message="Request validation failed"),
        details=details,
    ).model_dump()
    return JSONResponse(status_code=422, content=content)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(AuthenticationError, handle_authentication_error)
    app.add_exception_handler(ConflictError, handle_conflict_error)
    app.add_exception_handler(NotFoundError, handle_not_found_error)
    app.add_exception_handler(UpstreamInvalidResponseError, handle_invalid_upstream_response)
    app.add_exception_handler(UpstreamUnavailableError, handle_unavailable_upstream)
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
