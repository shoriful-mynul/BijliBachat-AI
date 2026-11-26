"""Meter checkpoint contract.

A checkpoint is a value captured at a moment. It is not a live feed from the meter.
A photo reading has no default confirmation state, so extraction cannot confirm itself.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.schemas.common import ApiModel, KilowattHours, TrustStatus, UtcTimestamp


class CaptureMethod(StrEnum):
    MANUAL = "manual"
    PHOTO = "photo"


class ConfirmationState(StrEnum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"


class MeterSource(ApiModel):
    """A short note about where the checkpoint came from. Not a file, a photo, or an OCR payload."""

    label: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=240)


class MeterReading(ApiModel):
    """One meter register checkpoint for one household.

    `confirmation_state` is required. Nothing in this model fills it in.
    A photo extraction should be sent as `pending_confirmation` until a person accepts it.
    Spike checks and register-order checks are not applied here.
    """

    id: UUID
    household_id: UUID
    register_kwh: KilowattHours
    read_at: UtcTimestamp
    capture_method: CaptureMethod
    confirmation_state: ConfirmationState
    trust_status: TrustStatus
    source: MeterSource | None = None
