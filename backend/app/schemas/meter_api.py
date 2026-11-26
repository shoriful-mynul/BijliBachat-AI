"""Meter capture and Cliff Guard contracts. The API does not retain readings."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ApiModel, KilowattHours, TrustStatus, UtcTimestamp
from app.schemas.meter_reading import CaptureMethod
from app.schemas.tariff import Eligibility, TariffType

ReviewDecision = Literal["keep_as_submitted"]
ValidationOutcome = Literal["accepted", "rejected", "needs_review"]
ThresholdStatus = Literal["verified", "needs_verification", "unavailable"]
StorageMode = Literal["not_retained"]


class ExtractedMeterField(ApiModel):
    value: str | None = None
    confidence: Literal["readable", "uncertain", "unreadable", "missing"]
    readable: bool
    note: str | None = Field(default=None, max_length=240)
    trust_status: TrustStatus


class MeterExtractionDraft(ApiModel):
    """An unconfirmed meter-photo reading. It is not saved."""

    confirmed: Literal[False] = False
    media_type: str
    model: str
    reading_kwh: ExtractedMeterField
    unit_label: ExtractedMeterField
    meter_reference: ExtractedMeterField
    requires_manual_review: bool
    limitations: list[str]


class LedgerReading(ApiModel):
    """A checkpoint the caller already holds. The API did not store it."""

    id: UUID
    register_kwh: KilowattHours
    read_at: UtcTimestamp
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    capture_method: CaptureMethod
    trust_status: TrustStatus


class NewMeterReading(ApiModel):
    confirmation: Literal["user_confirmed"]
    register_kwh: KilowattHours
    read_at: UtcTimestamp
    capture_method: CaptureMethod
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    origin: Literal["manual", "photo_confirmed", "photo_corrected"]
    review_decision: ReviewDecision | None = None


class SubmitMeterReadingRequest(ApiModel):
    household_id: UUID
    reading: NewMeterReading
    prior_readings: list[LedgerReading] = Field(default_factory=list, max_length=200)


class AcceptedCheckpoint(ApiModel):
    id: UUID
    household_id: UUID
    register_kwh: str
    read_at: UtcTimestamp
    capture_method: CaptureMethod
    confirmation_state: Literal["confirmed"]
    trust_status: TrustStatus
    meter_reference: str | None = None
    warnings: list[str]


class MeterValidationResponse(ApiModel):
    accepted: bool
    outcome: ValidationOutcome
    explanation: str
    warnings: list[str]
    checkpoint: AcceptedCheckpoint | None = None
    storage: StorageMode = "not_retained"


class MeterLedgerNotice(ApiModel):
    storage: StorageMode = "not_retained"
    readings: list[AcceptedCheckpoint]
    limitation: str


class QuantityView(ApiModel):
    value: str | None = None
    trust_status: TrustStatus
    detail: str


class ReadingView(ApiModel):
    id: UUID
    register_kwh: str
    read_at: UtcTimestamp
    meter_reference: str | None = None
    trust_status: TrustStatus


class IntervalView(ApiModel):
    reading_id: UUID
    consumed_kwh: str | None = None
    trust_status: TrustStatus
    detail: str


class ProjectionView(ApiModel):
    status: Literal["estimated", "unavailable"]
    message: str
    projected_date: date | None = None
    trust_status: TrustStatus
    observation_period: str | None = None
    assumptions: list[str]


class CliffGuardRequest(ApiModel):
    as_of: UtcTimestamp
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    readings: list[LedgerReading] = Field(default_factory=list, max_length=200)
    provider_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
    consumer_category: str | None = Field(default=None, max_length=40)
    tariff_type: TariffType | None = None
    eligibility: Eligibility | None = None
    billing_date: date | None = None
    cycle_started_on: date | None = None
    cycle_ends_on: date | None = None
    cycle_start_register_kwh: KilowattHours | None = None


class CliffGuardResponse(ApiModel):
    storage: StorageMode = "not_retained"
    latest_reading: ReadingView | None = None
    previous_reading: ReadingView | None = None
    consumption_kwh: QuantityView
    observation_period: str | None = None
    average_daily_kwh: QuantityView
    billing_cycle_consumption_kwh: QuantityView
    billing_cycle_started_on: date | None = None
    billing_cycle_ends_on: date | None = None
    threshold_status: ThresholdStatus
    threshold_kwh: str | None = None
    threshold_source: str | None = None
    remaining_kwh: QuantityView
    remaining_days: QuantityView
    safe_daily_allowance_kwh: QuantityView
    projection: ProjectionView
    last_updated: datetime | None = None
    calculated_at: UtcTimestamp
    missing_inputs: list[str]
    limitations: list[str]
    warnings: list[str]
    intervals: list[IntervalView] = Field(default_factory=list)
