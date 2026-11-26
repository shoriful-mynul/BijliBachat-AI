"""Turn a meter-photo model response into an unconfirmed draft."""

import re
from decimal import Decimal, InvalidOperation

from app.integrations.gemini.errors import GeminiSchemaError
from app.integrations.gemini.meter_schema import METER_FIELDS
from app.schemas.common import TrustStatus
from app.schemas.meter_api import ExtractedMeterField, MeterExtractionDraft

_CONFIDENCE = {"readable", "uncertain", "unreadable", "missing"}


def parse_meter_extraction(payload: dict[str, object], *, media_type: str, model: str) -> MeterExtractionDraft:
    if not isinstance(payload, dict):
        raise GeminiSchemaError()
    fields = {name: _field(name, payload.get(name)) for name in METER_FIELDS}
    reading = fields["reading_kwh"]
    review = reading.confidence != "readable" or reading.value is None
    return MeterExtractionDraft(
        confirmed=False,
        media_type=media_type,
        model=model,
        reading_kwh=reading,
        unit_label=fields["unit_label"],
        meter_reference=fields["meter_reference"],
        requires_manual_review=review,
        limitations=[
            "This reading was taken from a photo and is not confirmed.",
            "An unreadable digit is blank, not zero.",
            "Confirm or correct the register before saving a checkpoint.",
        ],
    )


def _field(name: str, raw: object) -> ExtractedMeterField:
    if not isinstance(raw, dict):
        raise GeminiSchemaError()
    confidence = raw.get("confidence")
    if confidence not in _CONFIDENCE:
        raise GeminiSchemaError()
    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        raise GeminiSchemaError()
    value = raw.get("value")
    if value is not None and not isinstance(value, str):
        raise GeminiSchemaError()
    text = value.strip() if isinstance(value, str) and value.strip() else None
    if confidence in {"unreadable", "missing"}:
        text = None
    if text is None:
        return ExtractedMeterField(
            value=None,
            confidence="missing" if confidence == "readable" else confidence,  # type: ignore[arg-type]
            readable=False,
            note=note if isinstance(note, str) and note.strip() else None,
            trust_status=TrustStatus.UNAVAILABLE,
        )
    normalized, extra = _normalize(name, text)
    combined = " ".join(part for part in (note if isinstance(note, str) else None, extra) if part)
    if normalized is None:
        return ExtractedMeterField(
            value=None,
            confidence="unreadable",
            readable=False,
            note=(combined or "The display could not be read as a register value.")[:240],
            trust_status=TrustStatus.UNAVAILABLE,
        )
    return ExtractedMeterField(
        value=normalized,
        confidence=confidence,  # type: ignore[arg-type]
        readable=True,
        note=combined[:240] or None,
        trust_status=TrustStatus.EXTRACTED,
    )


def _normalize(name: str, text: str) -> tuple[str | None, str | None]:
    if name == "reading_kwh":
        cleaned = text.replace(",", "")
        if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
            return None, "The display was not a plain decimal."
        try:
            number = Decimal(cleaned)
        except InvalidOperation:
            return None, "The display was not a plain decimal."
        exponent = number.as_tuple().exponent
        scale = -exponent if isinstance(exponent, int) and exponent < 0 else 0
        if scale > 3:
            return None, "The display has more than three decimal places."
        return f"{number:.3f}", None
    if name == "meter_reference":
        compact = re.sub(r"\s+", "", text)
        if re.fullmatch(r"[A-Za-z0-9-]{4,32}", compact):
            return compact, None
        return None, "The meter number was not clearly readable."
    label = text.strip()
    if name == "unit_label" and len(label) <= 40:
        return label, None
    return None, None
