from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.common import TrustStatus
from app.schemas.meter_reading import CaptureMethod, ConfirmationState, MeterReading

READING_ID = UUID("8c2d4e60-1f3a-4b5c-9d70-2b4c6d8e0f1a")
HOUSEHOLD_ID = UUID("3b1f2a44-0c3e-4d5b-8e7f-1a2b3c4d5e6f")


def reading(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": str(READING_ID),
        "household_id": str(HOUSEHOLD_ID),
        "register_kwh": "15482.500",
        "read_at": "2026-11-18T15:30:00+05:00",
        "capture_method": "manual",
        "confirmation_state": "confirmed",
        "trust_status": "Verified",
    }
    payload.update(overrides)
    return payload


def test_manual_reading_preserves_decimal_precision_and_utc() -> None:
    checkpoint = MeterReading.model_validate(reading())

    assert checkpoint.id == READING_ID
    assert checkpoint.household_id == HOUSEHOLD_ID
    assert checkpoint.register_kwh == Decimal("15482.500")
    assert checkpoint.read_at == datetime(2026, 11, 18, 10, 30, tzinfo=timezone.utc)
    assert checkpoint.capture_method is CaptureMethod.MANUAL
    assert checkpoint.confirmation_state is ConfirmationState.CONFIRMED
    assert checkpoint.trust_status is TrustStatus.VERIFIED
    assert checkpoint.source is None

    serialized = checkpoint.model_dump(mode="json")
    assert serialized["register_kwh"] == "15482.500"
    again = MeterReading.model_validate(serialized)
    assert again.register_kwh == checkpoint.register_kwh


def test_photo_reading_requires_an_explicit_confirmation_state() -> None:
    payload = reading(
        capture_method="photo",
        confirmation_state="pending_confirmation",
        trust_status="Extracted",
        source={"label": "photo checkpoint", "note": "Waiting for the household to accept it."},
    )
    checkpoint = MeterReading.model_validate(payload)

    assert checkpoint.confirmation_state is ConfirmationState.PENDING_CONFIRMATION
    assert checkpoint.trust_status is TrustStatus.EXTRACTED
    assert checkpoint.source is not None
    assert checkpoint.source.label == "photo checkpoint"

    incomplete = dict(payload)
    del incomplete["confirmation_state"]
    with pytest.raises(ValidationError):
        MeterReading.model_validate(incomplete)


@pytest.mark.parametrize("label", ["Verified", "Calculated", "Extracted", "Estimated", "Unavailable"])
def test_trust_status_accepts_only_the_named_labels(label: str) -> None:
    checkpoint = MeterReading.model_validate(reading(trust_status=label))

    assert checkpoint.trust_status.value == label


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "reading-1"},
        {"household_id": "home"},
        {"register_kwh": "-0.1"},
        {"register_kwh": "1.2345"},
        {"register_kwh": 10.5},
        {"register_kwh": "1e2"},
        {"register_kwh": True},
        {"read_at": "2026-11-18T15:30:00"},
        {"capture_method": "live"},
        {"confirmation_state": "approved"},
        {"trust_status": "verified"},
        {"trust_status": "Safe"},
        {"source": {"label": "photo", "image_base64": "aaaa"}},
        {"ocr_text": "15482"},
    ],
)
def test_meter_reading_rejects_malformed_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MeterReading.model_validate(reading(**overrides))


def test_meter_reading_has_no_live_feed_field() -> None:
    assert "live" not in MeterReading.model_fields
    assert "capture_method" in MeterReading.model_fields
