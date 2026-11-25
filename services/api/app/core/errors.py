"""Standard error responses and domain exception types."""

import uuid
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Structured domain exception matching API_SPEC.md error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": _get_request_id(request),
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHENTICATED"
    elif exc.status_code == 403:
        code = "UNAUTHORIZED"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 409:
        code = "CONFLICT"
    elif exc.status_code == 429:
        code = "RATE_LIMIT_EXCEEDED"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "request_id": _get_request_id(request),
            }
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = "; ".join(
        f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', 'invalid')}"
        for err in exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": details or "Invalid request payload.",
                "request_id": _get_request_id(request),
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal error occurred.",
                "request_id": _get_request_id(request),
            }
        },
    )
