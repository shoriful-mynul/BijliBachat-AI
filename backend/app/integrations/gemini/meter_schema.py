"""JSON schema for a meter photo. This is not an electricity-bill extraction."""

METER_INSTRUCTIONS = (
    "Read the electricity meter in this photo. "
    "Return the visible register as a plain decimal string, or null when any digit is unreadable. "
    "An unreadable digit is null, not zero. "
    "Return the unit label and meter number only when they are visible. "
    "Set confidence to readable, uncertain, unreadable, or missing. "
    "Add a short note for glare, blur, or an ambiguous digit. "
    "Do not calculate consumption, choose a tariff, or decide what the household used."
)

_FIELD = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "confidence": {
            "type": "string",
            "enum": ["readable", "uncertain", "unreadable", "missing"],
        },
        "note": {"type": ["string", "null"]},
    },
    "required": ["value", "confidence", "note"],
}

METER_FIELDS = ("reading_kwh", "unit_label", "meter_reference")

METER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {name: _FIELD for name in METER_FIELDS},
    "required": list(METER_FIELDS),
}
