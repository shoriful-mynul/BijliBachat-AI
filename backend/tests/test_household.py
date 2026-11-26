from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.household import HouseholdProfile

HOUSEHOLD_ID = UUID("3b1f2a44-0c3e-4d5b-8e7f-1a2b3c4d5e6f")


def household(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": str(HOUSEHOLD_ID),
        "display_name": "Gulberg home",
        "provider_code": "example-disco",
        "service_region": "Lahore",
        "created_at": "2026-11-01T00:00:00+05:00",
        "updated_at": "2026-11-18T10:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_household_accepts_an_open_provider_code_and_stores_utc() -> None:
    profile = HouseholdProfile.model_validate(
        household(provider_code="future_company-2", display_name="  Gulberg home  ")
    )

    assert profile.id == HOUSEHOLD_ID
    assert profile.display_name == "Gulberg home"
    assert profile.provider_code == "future_company-2"
    assert profile.service_region == "Lahore"
    assert profile.created_at == datetime(2026, 10, 31, 19, 0, tzinfo=timezone.utc)
    assert profile.updated_at == datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)
    assert set(HouseholdProfile.model_fields) == {
        "id",
        "display_name",
        "provider_code",
        "service_region",
        "created_at",
        "updated_at",
    }


def test_household_allows_a_missing_region() -> None:
    profile = HouseholdProfile.model_validate(household(service_region=None))

    assert profile.service_region is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "not-a-uuid"},
        {"display_name": "   "},
        {"display_name": "x" * 81},
        {"provider_code": ""},
        {"provider_code": "has space"},
        {"provider_code": "-leading"},
        {"provider_code": "a" * 33},
        {"service_region": ""},
        {"created_at": "2026-11-01T00:00:00"},
        {"updated_at": "2026-10-01T00:00:00Z"},
        {"protected_consumer": True},
        {"address": "12 Example Road"},
    ],
)
def test_household_rejects_malformed_or_unexpected_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HouseholdProfile.model_validate(household(**overrides))
