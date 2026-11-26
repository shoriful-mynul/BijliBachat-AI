"""Configurable limit for bill and meter file checks.

The forwarding header is ignored unless the immediate peer is listed in
`TRUSTED_PROXIES`. This limiter lives in one process and does not protect
every replica of a hosted API.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.rate_limit import client_address
from app.schemas.errors import ErrorCode, ErrorResponse


def extraction_limited(request: Request) -> JSONResponse | None:
    limiter = getattr(request.app.state, "extract_limiter", None)
    if limiter is None:
        return None
    settings = request.app.state.settings
    trusted = frozenset(getattr(settings, "trusted_proxies", []))
    peer = request.client.host if request.client else None
    key = client_address(peer, request.headers.get("x-forwarded-for"), trusted)
    if limiter.allow(key):
        return None
    body = ErrorResponse(
        code=ErrorCode.UNAVAILABLE,
        message="Too many file checks from this network. Wait a minute and try again.",
    )
    return JSONResponse(status_code=429, content=body.model_dump(mode="json"))
