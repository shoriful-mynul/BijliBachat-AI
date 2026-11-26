from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.common import KilowattHours, MoneyAmount, TrustStatus


class QuantitySample(BaseModel):
    units: KilowattHours
    amount: MoneyAmount


def test_decimal_json_keeps_scale_and_rejects_binary_floats() -> None:
    sample = QuantitySample(units="148.500", amount="7150.20")

    assert sample.units == Decimal("148.500")
    assert sample.amount == Decimal("7150.20")
    assert sample.model_dump(mode="json") == {"units": "148.500", "amount": "7150.20"}

    restored = QuantitySample.model_validate(sample.model_dump(mode="json"))
    assert restored.units == sample.units
    assert restored.amount == sample.amount


def test_whole_numbers_are_accepted() -> None:
    sample = QuantitySample(units=148, amount=7150)

    assert sample.units == Decimal("148")
    assert sample.amount == Decimal("7150")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("units", 0.1),
        ("amount", 1.2),
        ("units", "1e3"),
        ("amount", "10.235"),
        ("units", "-1"),
        ("amount", "NaN"),
        ("units", "inf"),
    ],
)
def test_decimal_fields_reject_unsafe_values(field: str, value: object) -> None:
    payload = {"units": "1.000", "amount": "1.00", field: value}
    with pytest.raises(ValidationError):
        QuantitySample.model_validate(payload)


def test_trust_status_rejects_unknown_spellings() -> None:
    with pytest.raises(ValueError):
        TrustStatus("verified")
    with pytest.raises(ValueError):
        TrustStatus("Estimated ")
    assert [status.value for status in TrustStatus] == [
        "Verified",
        "Calculated",
        "Extracted",
        "Estimated",
        "Unavailable",
    ]
