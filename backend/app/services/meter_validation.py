"""Check a confirmed checkpoint against the caller's earlier checkpoints.

The submitted register is never rewritten. A warning leaves the value as entered.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.schemas.common import TrustStatus
from app.schemas.meter_api import (
    AcceptedCheckpoint,
    LedgerReading,
    MeterValidationResponse,
    NewMeterReading,
)
from app.schemas.meter_reading import MeterReading

# A review flag, not a tariff rule and not evidence of manipulation.
ANOMALY_DAILY_RATIO = Decimal("3")


def validate_reading(
    *,
    household_id: UUID,
    reading: NewMeterReading,
    prior_readings: list[LedgerReading],
) -> MeterValidationResponse:
    same = sorted(
        (item for item in prior_readings if _meter_key(item.meter_reference) == _meter_key(reading.meter_reference)),
        key=lambda item: item.read_at,
    )
    if any(item.read_at == reading.read_at for item in same):
        return _rejected("This checkpoint matches the time of a reading already kept for this meter.")
    if any(
        item.read_at.date() == reading.read_at.date() and item.register_kwh == reading.register_kwh for item in same
    ):
        return _rejected("This checkpoint repeats the same register value on the same day for this meter.")
    if same and reading.read_at < same[-1].read_at:
        return _rejected(
            "This checkpoint is earlier than the latest reading for this meter. "
            "It was not inserted between older checkpoints."
        )
    if not same:
        return _accept(household_id, reading, [])

    previous = same[-1]
    warnings: list[str] = []
    if reading.register_kwh < previous.register_kwh:
        warnings.append(
            "The register is lower than the previous checkpoint for this meter. "
            "That can happen after a meter replacement, a rollover, a correction, or a typing error. "
            "This check does not choose one of those explanations."
        )
    elif len(same) >= 2 and _is_anomaly(same[-2], previous, reading):
        warnings.append(
            "Possible reading anomaly. The daily pace since the previous checkpoint is more than "
            f"{ANOMALY_DAILY_RATIO} times the pace of the checkpoint before it. "
            "The register was not changed."
        )
    if warnings and reading.review_decision != "keep_as_submitted":
        return MeterValidationResponse(
            accepted=False,
            outcome="needs_review",
            explanation=warnings[0],
            warnings=warnings,
            checkpoint=None,
        )
    return _accept(household_id, reading, warnings)


def _accept(household_id: UUID, reading: NewMeterReading, warnings: list[str]) -> MeterValidationResponse:
    trust = TrustStatus.EXTRACTED if reading.origin == "photo_confirmed" else TrustStatus.VERIFIED
    checkpoint = MeterReading(
        id=uuid4(),
        household_id=household_id,
        register_kwh=reading.register_kwh,
        read_at=reading.read_at,
        capture_method=reading.capture_method,
        confirmation_state="confirmed",
        trust_status=trust,
        source=None,
    )
    return MeterValidationResponse(
        accepted=True,
        outcome="accepted",
        explanation="The checkpoint was confirmed by you. This API does not keep it.",
        warnings=warnings,
        checkpoint=AcceptedCheckpoint(
            id=checkpoint.id,
            household_id=checkpoint.household_id,
            register_kwh=f"{checkpoint.register_kwh:.3f}",
            read_at=checkpoint.read_at,
            capture_method=checkpoint.capture_method,
            confirmation_state="confirmed",
            trust_status=checkpoint.trust_status,
            meter_reference=reading.meter_reference,
            warnings=warnings,
        ),
    )


def _rejected(explanation: str) -> MeterValidationResponse:
    return MeterValidationResponse(
        accepted=False,
        outcome="rejected",
        explanation=explanation,
        warnings=[],
        checkpoint=None,
    )


def _is_anomaly(earlier: LedgerReading, previous: LedgerReading, reading: NewMeterReading) -> bool:
    previous_days = _elapsed_days(earlier.read_at, previous.read_at)
    current_days = _elapsed_days(previous.read_at, reading.read_at)
    if previous_days < 1 or current_days < 1:
        return False
    previous_rate = (previous.register_kwh - earlier.register_kwh) / previous_days
    current_rate = (reading.register_kwh - previous.register_kwh) / current_days
    if previous_rate <= 0:
        return False
    return current_rate > previous_rate * ANOMALY_DAILY_RATIO


def _elapsed_days(start: datetime, end: datetime) -> Decimal:
    delta = end - start
    seconds = Decimal(delta.days) * Decimal(86400) + Decimal(delta.seconds) + Decimal(delta.microseconds) / Decimal(1000000)
    if seconds <= 0:
        return Decimal(0)
    return seconds / Decimal(86400)


def _meter_key(reference: str | None) -> str:
    if reference is None or not reference.strip():
        return ""
    return reference.strip().casefold()


def utc_now() -> datetime:
    return datetime.now(UTC)
