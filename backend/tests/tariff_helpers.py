"""Synthetic tariff fixtures. These rates are not Pakistani tariffs."""

from app.schemas.tariff import TariffCalculationRequest
from app.tariffs.loader import TariffCatalog
from app.tariffs.models import TariffConfig

SOURCE = {
    "issuing_authority": "Synthetic fixture authority",
    "document_title": "Synthetic tariff fixture",
    "source_url": "https://example.com/synthetic-tariff-fixture",
    "notification_date": "2026-01-01",
    "retrieval_date": "2026-01-02",
    "reference": "Test fixture, not an official schedule",
    "verification_status": "verified",
    "limitations": ["Synthetic fixture. Not a Pakistani tariff."],
}

ROUNDING = {
    "money_quantum": "0.01",
    "mode": "half_up",
    "stage": "component",
    "source_status": "engine_convention",
    "note": "Synthetic configs round each money component to the nearest paisa, half up.",
}


def payload(**overrides: object) -> dict:
    document = {
        "config_id": "synthetic-single",
        "version": "synthetic-1",
        "provider_code": "SYNTH",
        "consumer_category": "residential",
        "tariff_type": "non_tou",
        "eligibility": "unprotected",
        "schedule_name": "Synthetic schedule",
        "billing_frequency": "monthly",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "slab_method": "single_slab",
        "verification_status": "verified",
        "synthetic": True,
        "rounding": dict(ROUNDING),
        "slabs": [
            {
                "lower_exclusive_kwh": "0",
                "upper_inclusive_kwh": None,
                "rate_per_kwh": "10.00",
            }
        ],
        "fixed_charge": {
            "state": "not_applicable",
            "reason": "This synthetic fixture has no fixed charge.",
        },
        "minimum_charge": {
            "state": "not_applicable",
            "reason": "This synthetic fixture has no minimum charge.",
        },
        "time_of_use": None,
        "adjustments": [percent_adjustment()],
        "source": dict(SOURCE),
    }
    document.update(overrides)
    return document


def percent_adjustment(**overrides: object) -> dict:
    item = {
        "code": "gst",
        "label": "Synthetic tax",
        "state": "applicable_verified",
        "required_for_payable": True,
        "basis": "percent_of_components",
        "percent": "18.00",
        "applies_to": ["energy_charge"],
        "reason": "Synthetic tax rate. Not a Pakistan tax.",
    }
    item.update(overrides)
    return item


def unavailable_adjustment(code: str = "gst", label: str = "GST") -> dict:
    return {
        "code": code,
        "label": label,
        "state": "unavailable",
        "required_for_payable": True,
        "reason": "Synthetic stand-in for a component whose rate is unknown.",
    }


def make_config(**overrides: object) -> TariffConfig:
    return TariffConfig.model_validate(payload(**overrides))


def make_catalog(*configs: TariffConfig) -> TariffCatalog:
    return TariffCatalog(configs=tuple(configs), availability=())


def request(**overrides: object) -> TariffCalculationRequest:
    body = {
        "provider_code": "SYNTH",
        "consumer_category": "residential",
        "tariff_type": "non_tou",
        "eligibility": "unprotected",
        "billing_date": "2026-06-01",
        "consumption_kwh": "10",
    }
    body.update(overrides)
    return TariffCalculationRequest.model_validate(body)
