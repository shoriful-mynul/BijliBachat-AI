"""Request and response contracts.

Household and meter models describe future records. They are not stored,
and no route accepts them yet.
"""

from app.schemas.common import KilowattHours, MoneyAmount, TrustStatus, UtcTimestamp
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.household import HouseholdProfile
from app.schemas.meter_reading import (
    CaptureMethod,
    ConfirmationState,
    MeterReading,
    MeterSource,
)

__all__ = [
    "CaptureMethod",
    "ConfirmationState",
    "ErrorCode",
    "ErrorResponse",
    "HouseholdProfile",
    "KilowattHours",
    "MeterReading",
    "MeterSource",
    "MoneyAmount",
    "TrustStatus",
    "UtcTimestamp",
]
