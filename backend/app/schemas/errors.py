"""Application error contract.

FastAPI validation errors stay in their own shape (`detail` is a list of field errors).
This model is for failures the application reports, including an unexpected server error.
"""

from enum import StrEnum

from pydantic import Field

from app.schemas.common import ApiModel


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"
    INTERNAL_ERROR = "internal_error"


class ErrorResponse(ApiModel):
    """A safe error body. It does not carry a traceback or a household record."""

    code: ErrorCode
    message: str = Field(min_length=1, max_length=300)
