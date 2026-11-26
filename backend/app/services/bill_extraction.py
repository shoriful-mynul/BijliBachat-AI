"""Turn a Gemini object into an unconfirmed draft. Missing values stay empty."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.integrations.gemini.errors import GeminiSchemaError
from app.integrations.gemini.schema import FIELD_NAMES
from app.schemas.bill import BillExtractionDraft, ExtractedCharge, ExtractedField
from app.schemas.common import TrustStatus

_CONFIDENCE = {"readable", "uncertain", "unreadable", "missing"}
_TARIFF_TYPES = {
    "non_tou": "non_tou",
    "nontou": "non_tou",
    "non-tou": "non_tou",
    "tou": "tou",
    "timeofuse": "tou",
    "time of use": "tou",
}
_ELIGIBILITY = {"lifeline": "lifeline", "protected": "protected", "unprotected": "unprotected"}
_PROVIDERS = {
    "IESCO": "IESCO",
    "ISLAMABADELECTRICSUPPLYCOMPANY": "IESCO",
    "LESCO": "LESCO",
    "LAHOREELECTRICSUPPLYCOMPANY": "LESCO",
    "KE": "KE",
    "KELECTRIC": "KE",
    "HESCO": "HESCO",
}
_MONEY_FIELDS = {
    "energy_charge",
    "fixed_charge",
    "fuel_price_adjustment",
    "gst",
    "electricity_duty",
    "tv_fee",
    "arrears",
    "total_amount_due",
}
_QUANTITY_FIELDS = {
    "consumption_kwh",
    "peak_kwh",
    "off_peak_kwh",
    "current_reading_kwh",
    "previous_reading_kwh",
    "sanctioned_load_kw",
}
_DATE_FIELDS = {"billing_date", "due_date"}


def parse_extraction(payload: dict[str, object], *, media_type: str, model: str) -> BillExtractionDraft:
    if not isinstance(payload, dict):
        raise GeminiSchemaError()
    fields: dict[str, ExtractedField] = {}
    for name in FIELD_NAMES:
        raw = payload.get(name)
        if not isinstance(raw, dict):
            raise GeminiSchemaError()
        fields[name] = _field(name, raw)
    other = payload.get("other_charges", [])
    if other is None:
        other = []
    if not isinstance(other, list):
        raise GeminiSchemaError()
    charges = [_charge(item) for item in other[:8]]
    return BillExtractionDraft(
        confirmed=False,
        media_type=media_type,
        model=model,
        other_charges=charges,
        limitations=[
            "These values were read from the document and are not confirmed.",
            "A blank field was not treated as zero.",
            "Confirm or correct every value before requesting an audit.",
        ],
        **fields,
    )


def _field(name: str, raw: dict[str, object]) -> ExtractedField:
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
        return _empty(confidence if confidence != "readable" else "missing", note)
    normalized, extra = _normalize(name, text)
    combined = _join_notes(note, extra)
    if normalized is None:
        return ExtractedField(
            value=None,
            confidence="unreadable",
            readable=False,
            note=combined or "The printed value could not be read as a structured field.",
            trust_status=TrustStatus.UNAVAILABLE,
        )
    uncertain = confidence == "uncertain"
    return ExtractedField(
        value=normalized,
        confidence="uncertain" if uncertain else "readable",
        readable=True,
        note=combined,
        trust_status=TrustStatus.EXTRACTED,
    )


def _empty(confidence: str, note: object) -> ExtractedField:
    return ExtractedField(
        value=None,
        confidence=confidence,  # type: ignore[arg-type]
        readable=False,
        note=note if isinstance(note, str) and note.strip() else None,
        trust_status=TrustStatus.UNAVAILABLE,
    )


def _normalize(name: str, text: str) -> tuple[str | None, str | None]:
    if name == "provider_code":
        key = re.sub(r"[^A-Z0-9]", "", text.upper())
        if key in _PROVIDERS:
            return _PROVIDERS[key], None
        return None, "The printed provider was not mapped to a company code."
    if name == "tariff_type":
        key = text.strip().lower()
        compact = re.sub(r"[^a-z]", "", key)
        mapped = _TARIFF_TYPES.get(key) or _TARIFF_TYPES.get(compact)
        if mapped:
            return mapped, None
        return None, "The printed tariff type was not an explicit non-ToU or ToU label."
    if name == "eligibility":
        key = text.strip().lower()
        if key in _ELIGIBILITY:
            return _ELIGIBILITY[key], None
        return None, "Consumer category eligibility was not explicitly printed."
    if name == "consumer_category":
        key = text.strip().lower()
        if key in {"residential", "domestic"}:
            return "residential", None
        if re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", key):
            return key, None
        return None, "The printed consumer category was not a structured category."
    if name in _DATE_FIELDS:
        try:
            return date.fromisoformat(text).isoformat(), None
        except ValueError:
            return None, "The printed date was not an unambiguous calendar date."
    if name in _MONEY_FIELDS or name in _QUANTITY_FIELDS:
        return _decimal_text(text, places=2 if name in _MONEY_FIELDS else 3)
    if name == "meter_number":
        compact = re.sub(r"\s+", "", text)
        if re.fullmatch(r"[A-Za-z0-9-]{4,32}", compact):
            return compact, None
        return None, "The meter number was not clearly readable."
    return None, None


def _decimal_text(text: str, *, places: int) -> tuple[str | None, str | None]:
    cleaned = text.replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return None, "The printed number was not a plain decimal."
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None, "The printed number was not a plain decimal."
    exponent = number.as_tuple().exponent
    scale = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    if scale > places:
        return None, "The printed number had more decimal places than this field allows."
    return f"{number:.{places}f}", None


def _charge(item: object) -> ExtractedCharge:
    if not isinstance(item, dict):
        raise GeminiSchemaError()
    label = item.get("label")
    if not isinstance(label, str) or not label.strip():
        raise GeminiSchemaError()
    parsed = _field("energy_charge", item)
    return ExtractedCharge(
        label=label.strip()[:80],
        value=parsed.value,
        confidence=parsed.confidence,
        readable=parsed.readable,
        note=parsed.note,
        trust_status=parsed.trust_status,
    )


def _join_notes(left: object, right: str | None) -> str | None:
    parts = [part.strip() for part in (left, right) if isinstance(part, str) and part.strip()]
    if not parts:
        return None
    return " ".join(parts)[:240]
