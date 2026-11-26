"""Shared contract types. These validate shape and precision. They do not calculate a bill."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field


class ApiModel(BaseModel):
    """Rejects unknown fields. Strings are stripped before length checks."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TrustStatus(StrEnum):
    """How a number should be read. The spelling is the contract."""

    VERIFIED = "Verified"
    CALCULATED = "Calculated"
    EXTRACTED = "Extracted"
    ESTIMATED = "Estimated"
    UNAVAILABLE = "Unavailable"


def _reject_unsafe_decimal_input(value: object) -> object:
    if isinstance(value, bool):
        raise ValueError("Enter a decimal string or a whole number.")
    if isinstance(value, float):
        raise ValueError(
            "Enter a decimal string or a whole number. Binary floats are not accepted."
        )
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("Enter a decimal string or a whole number.")
        if "e" in stripped.lower():
            raise ValueError("Use a plain decimal number, not scientific notation.")
        return stripped
    return value


def _as_utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone.")
    return value.astimezone(timezone.utc)


KilowattHours = Annotated[
    Decimal,
    BeforeValidator(_reject_unsafe_decimal_input),
    Field(
        ge=0,
        max_digits=12,
        decimal_places=3,
        description="Meter or consumption quantity in kWh. Send a decimal string.",
    ),
]

MoneyAmount = Annotated[
    Decimal,
    BeforeValidator(_reject_unsafe_decimal_input),
    Field(
        ge=0,
        max_digits=14,
        decimal_places=2,
        description="A non-negative rupee amount. Send a decimal string. This type does not calculate one.",
    ),
]

UtcTimestamp = Annotated[
    AwareDatetime,
    AfterValidator(_as_utc),
]
