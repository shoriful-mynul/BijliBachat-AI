"""Map unexpected failures to the public error contract.

Validation errors and HTTP errors keep FastAPI's own responses.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.schemas.errors import ErrorCode, ErrorResponse

logger = logging.getLogger("bijlibachat.api")

_PUBLIC_FAILURE = "The request could not be completed."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> Response:
        # Keep FastAPI's field errors and HTTP status bodies when a broad handler also matches.
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        if isinstance(exc, StarletteHTTPException):
            return await http_exception_handler(request, exc)

        # The exception text can contain a household value or a secret. Log the type only.
        logger.error(
            "request_failed method=%s path=%s exception_type=%s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        body = ErrorResponse(code=ErrorCode.INTERNAL_ERROR, message=_PUBLIC_FAILURE)
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))
