"""Configurable limit for bill and meter file checks."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas.errors import ErrorCode, ErrorResponse


def extraction_limited(request: Request) -> JSONResponse | None:
    limiter = getattr(request.app.state, "extract_limiter", None)
    if limiter is None:
        return None
    forwarded = request.headers.get("x-forwarded-for", "")
    host = request.client.host if request.client else "local"
    key = forwarded.split(",")[0].strip() or host
    if limiter.allow(key):
        return None
    body = ErrorResponse(
        code=ErrorCode.UNAVAILABLE,
        message="Too many file checks from this network. Wait a minute and try again.",
    )
    return JSONResponse(status_code=429, content=body.model_dump(mode="json"))
