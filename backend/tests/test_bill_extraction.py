import pytest

from app.integrations.gemini.errors import GeminiSchemaError
from app.schemas.common import TrustStatus
from app.services.bill_extraction import parse_extraction
from tests.bill_samples import extraction_payload, field


def test_valid_extraction_stays_unconfirmed() -> None:
    draft = parse_extraction(extraction_payload(), media_type="image/png", model="gemini-3.8-flash")

    assert draft.confirmed is False
    assert draft.provider_code.value == "IESCO"
    assert draft.provider_code.trust_status == TrustStatus.EXTRACTED
    assert draft.energy_charge.value == "8275.00"
    assert "confirmed" in " ".join(draft.limitations).lower()


def test_missing_and_unreadable_fields_are_not_zero() -> None:
    draft = parse_extraction(
        extraction_payload(
            gst=field("0", "missing"),
            current_reading_kwh=field("4412", "unreadable"),
            fuel_price_adjustment=field(None, "uncertain", "The line is faint."),
        ),
        media_type="application/pdf",
        model="gemini-3.8-flash",
    )

    assert draft.gst.value is None
    assert draft.gst.trust_status == TrustStatus.UNAVAILABLE
    assert draft.current_reading_kwh.value is None
    assert draft.fuel_price_adjustment.value is None


def test_ambiguous_decimal_and_provider_are_left_blank() -> None:
    draft = parse_extraction(
        extraction_payload(
            energy_charge=field("about 8000", "uncertain"),
            provider_code=field("Some other utility", "readable"),
        ),
        media_type="image/jpeg",
        model="gemini-3.8-flash",
    )

    assert draft.energy_charge.value is None
    assert draft.energy_charge.confidence == "unreadable"
    assert draft.provider_code.value is None
    assert "company code" in (draft.provider_code.note or "")


def test_invalid_json_shape_and_unknown_confidence_are_rejected() -> None:
    with pytest.raises(GeminiSchemaError):
        parse_extraction({"provider_code": "IESCO"}, media_type="image/png", model="gemini-3.8-flash")
    broken = extraction_payload(energy_charge={"value": "10", "confidence": "sure", "note": None})
    with pytest.raises(GeminiSchemaError):
        parse_extraction(broken, media_type="image/png", model="gemini-3.8-flash")
    with pytest.raises(GeminiSchemaError):
        parse_extraction(extraction_payload(gst={"value": {"amount": 1}, "confidence": "readable", "note": None}), media_type="image/png", model="gemini-3.8-flash")
