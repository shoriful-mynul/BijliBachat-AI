"""Tiny file signatures for upload tests. They are not real electricity bills."""

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 12 + b"\xff\xd9"
WEBP = b"RIFF" + b"\x0c\x00\x00\x00" + b"WEBP" + b"VP8 "
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def field(value: str | None, confidence: str = "readable", note: str | None = None) -> dict:
    return {"value": value, "confidence": confidence, "note": note}


def extraction_payload(**overrides: object) -> dict:
    body = {
        "provider_code": field("IESCO"),
        "consumer_category": field("residential"),
        "tariff_type": field("non_tou"),
        "eligibility": field("unprotected"),
        "billing_date": field("2026-03-01"),
        "due_date": field(None, "missing"),
        "meter_number": field(None, "missing"),
        "consumption_kwh": field("250"),
        "peak_kwh": field(None, "missing"),
        "off_peak_kwh": field(None, "missing"),
        "current_reading_kwh": field(None, "unreadable", "The dial is blurred."),
        "previous_reading_kwh": field(None, "missing"),
        "sanctioned_load_kw": field("5"),
        "energy_charge": field("8275.00"),
        "fixed_charge": field("1750.00"),
        "fuel_price_adjustment": field(None, "missing"),
        "gst": field(None, "missing"),
        "electricity_duty": field(None, "missing"),
        "tv_fee": field(None, "missing"),
        "arrears": field(None, "missing"),
        "total_amount_due": field("12000.00"),
        "other_charges": [],
    }
    body.update(overrides)
    return body
