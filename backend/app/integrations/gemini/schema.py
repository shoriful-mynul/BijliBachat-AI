"""JSON schema sent to Gemini. Money values are strings so they are not floats."""

EXTRACTION_INSTRUCTIONS = (
    "Read this electricity bill and extract only values that are visible. "
    "Use a decimal string for money and kilowatt-hours, or null when a value is not visible. "
    "A missing charge is null, not zero. "
    "Set confidence to readable, uncertain, unreadable, or missing. "
    "Add a short note when a field is ambiguous. "
    "Do not calculate a bill, choose a tariff slab, decide whether a consumer is protected, "
    "invent a tax rate, or judge the document. "
    "Do not mark any field as confirmed."
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

_CHARGE = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "value": {"type": ["string", "null"]},
        "confidence": {
            "type": "string",
            "enum": ["readable", "uncertain", "unreadable", "missing"],
        },
        "note": {"type": ["string", "null"]},
    },
    "required": ["label", "value", "confidence", "note"],
}

FIELD_NAMES = (
    "provider_code",
    "consumer_category",
    "tariff_type",
    "eligibility",
    "billing_date",
    "due_date",
    "meter_number",
    "consumption_kwh",
    "peak_kwh",
    "off_peak_kwh",
    "current_reading_kwh",
    "previous_reading_kwh",
    "sanctioned_load_kw",
    "energy_charge",
    "fixed_charge",
    "fuel_price_adjustment",
    "gst",
    "electricity_duty",
    "tv_fee",
    "arrears",
    "total_amount_due",
)

GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        **{name: _FIELD for name in FIELD_NAMES},
        "other_charges": {"type": "array", "items": _CHARGE, "maxItems": 8},
    },
    "required": list(FIELD_NAMES),
}
