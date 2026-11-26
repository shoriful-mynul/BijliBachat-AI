"""Validate records before they are stored. This module does not calculate a bill."""

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, ValidationError

from app.schemas.appliance import ApplianceSpec
from app.schemas.bill import ConfirmedBillRequest
from app.schemas.common import ApiModel, KilowattHours, TrustStatus, UtcTimestamp
from app.schemas.history import CycleInput, SnapshotInput
from app.schemas.household import HouseholdProfile
from app.schemas.prediction import TargetKwh
from app.services.history import _elapsed, _exact_actual, _q


class StoredMeterCheckpoint(ApiModel):
    """A checkpoint a person already confirmed. An extraction draft is not this shape."""

    id: UUID
    household_id: UUID
    register_kwh: KilowattHours
    read_at: UtcTimestamp
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    capture_method: Literal["manual", "photo"]
    confirmation_state: Literal["confirmed"]
    trust_status: Literal["Calculated", "Extracted", "Estimated"]
    warnings: list[str] = Field(default_factory=list, max_length=12)


class StoredBillAudit(ApiModel):
    """A bill the person confirmed. Unconfirmed OCR is rejected by this shape."""

    id: UUID
    saved_at: UtcTimestamp
    confirmation: Literal["user_confirmed"]
    bill: ConfirmedBillRequest


class StoredHistoryCycle(ApiModel):
    id: UUID
    meter_reference: str = Field(pattern=r"^[A-Za-z0-9-]{4,32}$")
    start_checkpoint_id: UUID
    end_checkpoint_id: UUID
    started_at: UtcTimestamp
    ended_at: UtcTimestamp
    start_register_kwh: KilowattHours
    end_register_kwh: KilowattHours
    actual_kwh: KilowattHours
    duration_days: KilowattHours
    average_daily_kwh: KilowattHours
    trust_status: Literal["Calculated"]
    detail: str = Field(min_length=1, max_length=400)

    def measured_values_match(self) -> bool:
        cycle = CycleInput(
            id=self.id,
            meter_reference=self.meter_reference,
            start_checkpoint_id=self.start_checkpoint_id,
            end_checkpoint_id=self.end_checkpoint_id,
            started_at=self.started_at,
            ended_at=self.ended_at,
            start_register_kwh=self.start_register_kwh,
            end_register_kwh=self.end_register_kwh,
        )
        if self.start_checkpoint_id == self.end_checkpoint_id:
            return False
        if self.ended_at <= self.started_at:
            return False
        if self.end_register_kwh < self.start_register_kwh:
            return False
        elapsed = _elapsed(cycle)
        if elapsed <= 0:
            return False
        actual = _exact_actual(cycle)
        return (
            _q(actual) == f"{self.actual_kwh:.3f}"
            and _q(elapsed) == f"{self.duration_days:.3f}"
            and _q(actual / elapsed) == f"{self.average_daily_kwh:.3f}"
        )


class StoredBaseline(ApiModel):
    cycle_id: UUID
    target_kwh: TargetKwh


_MODELS: dict[str, type[ApiModel]] = {
    "household": HouseholdProfile,
    "meter_checkpoints": StoredMeterCheckpoint,
    "bill_audits": StoredBillAudit,
    "appliances": ApplianceSpec,
    "forecast_snapshots": SnapshotInput,
    "history_cycles": StoredHistoryCycle,
    "history_baselines": StoredBaseline,
}


def record_id_for(collection: str, model: ApiModel) -> str:
    if collection == "history_baselines":
        return str(model.cycle_id)  # type: ignore[attr-defined]
    return str(model.id)  # type: ignore[attr-defined]


def validate_record(collection: str, payload: object) -> tuple[dict[str, Any] | None, str | None]:
    """Return a JSON document, or a safe rejection reason. Values are not echoed."""
    model_type = _MODELS.get(collection)
    if model_type is None or not isinstance(payload, dict):
        return None, "The record did not match the saved shape."
    if "owner_uid" in payload or "uid" in payload:
        return None, "The record did not match the saved shape."
    try:
        model = model_type.model_validate(payload)
    except ValidationError:
        return None, "The record did not match the saved shape."
    if isinstance(model, StoredHistoryCycle) and not model.measured_values_match():
        return None, "The measured cycle did not match its checkpoints."
    if _promotes_trust(payload):
        return None, "The record did not match the saved shape."
    return model.model_dump(mode="json"), None


def _promotes_trust(payload: dict) -> bool:
    """Reject a body that tries to label an estimate as verified."""
    status = payload.get("trust_status")
    if status == TrustStatus.VERIFIED or status == "Verified":
        return True
    bill = payload.get("bill")
    if isinstance(bill, dict) and bill.get("trust_status") == "Verified":
        return True
    return False
