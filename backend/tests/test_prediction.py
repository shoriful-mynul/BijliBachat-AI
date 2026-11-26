from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

HOUSEHOLD_METER = "MTR-1001"


def _reading(register: str, when: datetime, reference: str = HOUSEHOLD_METER) -> dict:
    return {
        "id": str(uuid4()),
        "register_kwh": register,
        "read_at": when.isoformat(),
        "meter_reference": reference,
        "capture_method": "manual",
        "trust_status": "Verified",
    }


def _at(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 11, 1, hour, tzinfo=timezone.utc) + timedelta(days=day)


def _series() -> list[dict]:
    return [
        _reading("100.000", _at(0)),
        _reading("130.000", _at(3)),
        _reading("170.000", _at(7)),
    ]


def _forecast(client: TestClient, **overrides: object):
    body: dict[str, object] = {
        "as_of": _at(7).isoformat(),
        "meter_reference": HOUSEHOLD_METER,
        "readings": _series(),
        "cycle_started_on": "2026-11-01",
        "cycle_ends_on": "2026-11-15",
        "cycle_start_register_kwh": "100.000",
    }
    body.update(overrides)
    return client.post("/api/predictions/consumption", json=body)


def test_short_history_does_not_invent_a_forecast(client: TestClient) -> None:
    one = _forecast(client, readings=[_reading("100.000", _at(0))])
    two = _forecast(client, readings=[_reading("100.000", _at(0)), _reading("140.000", _at(8))])
    assert one.status_code == 200
    assert two.status_code == 200
    for response in (one, two):
        body = response.json()
        assert body["forecast_status"] == "unavailable"
        assert body["projected_cycle_kwh"]["value"] is None
        assert body["projected_cycle_kwh"]["trust_status"] == "Unavailable"
        assert body["series"] == []
        assert "three checkpoints" in " ".join(body["missing_inputs"])


def test_three_readings_shorter_than_seven_days_are_not_enough(client: TestClient) -> None:
    readings = [
        _reading("100.000", _at(0)),
        _reading("110.000", _at(3)),
        _reading("120.000", _at(6, 23)),
    ]
    body = _forecast(client, readings=readings, as_of=_at(6, 23).isoformat()).json()
    assert body["forecast_status"] == "unavailable"
    assert "seven complete days" in " ".join(body["missing_inputs"])
    assert body["projected_additional_kwh"]["value"] is None


def test_seven_day_forecast_uses_exact_pace_and_remaining_days(client: TestClient) -> None:
    body = _forecast(client).json()
    assert body["forecast_status"] == "estimated"
    assert body["average_daily_kwh"]["value"] == "10.000"
    assert body["average_daily_kwh"]["trust_status"] == "Calculated"
    assert body["cycle_consumption_kwh"]["value"] == "70.000"
    assert body["cycle_consumption_kwh"]["trust_status"] == "Calculated"
    assert body["remaining_days"] == "7"
    assert body["projected_additional_kwh"]["value"] == "70.000"
    assert body["projected_additional_kwh"]["trust_status"] == "Estimated"
    assert body["projected_cycle_kwh"]["value"] == "140.000"
    assert body["observation_period"] == "2026-11-01 to 2026-11-08"
    assert body["series"][-1]["kind"] == "estimated"
    assert body["series"][-1]["label"] == "Billing-cycle end"
    assert all(point["kind"] == "observed" for point in body["series"][:-1])
    assert "A 30-day month was not assumed." in body["projected_additional_kwh"]["detail"]
    assert "accuracy" not in " ".join(body["assumptions"]).lower() or "No accuracy" in " ".join(body["limitations"])


def test_rounding_uses_half_up_on_the_exact_result(client: TestClient) -> None:
    readings = [
        _reading("0.000", _at(0)),
        _reading("0.500", _at(3)),
        _reading("1.000", _at(7)),
    ]
    body = _forecast(
        client,
        readings=readings,
        cycle_start_register_kwh="0.000",
        cycle_ends_on="2026-11-11",
    ).json()
    assert body["average_daily_kwh"]["value"] == "0.143"
    assert body["projected_additional_kwh"]["value"] == "0.429"
    assert body["projected_cycle_kwh"]["value"] == "1.429"


def test_missing_cycle_start_register_blocks_the_forecast(client: TestClient) -> None:
    body = _forecast(client, cycle_start_register_kwh=None).json()
    assert body["forecast_status"] == "unavailable"
    assert body["cycle_consumption_kwh"]["value"] is None
    assert "start of the cycle" in " ".join(body["missing_inputs"])
    assert body["average_daily_kwh"]["value"] == "10.000"


def test_missing_and_reversed_cycle_dates(client: TestClient) -> None:
    missing = _forecast(client, cycle_started_on=None, cycle_ends_on=None).json()
    reversed_dates = _forecast(client, cycle_started_on="2026-11-20", cycle_ends_on="2026-11-01").json()
    assert missing["forecast_status"] == "unavailable"
    assert "start and end" in " ".join(missing["missing_inputs"])
    assert reversed_dates["forecast_status"] == "unavailable"
    assert "earlier than its start" in " ".join(reversed_dates["missing_inputs"])


def test_checkpoint_outside_the_cycle_is_not_used(client: TestClient) -> None:
    body = _forecast(client, cycle_started_on="2026-11-10", cycle_ends_on="2026-11-20").json()
    assert body["forecast_status"] == "unavailable"
    assert body["cycle_consumption_kwh"]["value"] is None
    assert "outside" in " ".join(body["missing_inputs"])


def test_register_decrease_is_not_corrected(client: TestClient) -> None:
    readings = [
        _reading("100.000", _at(0)),
        _reading("80.000", _at(4)),
        _reading("140.000", _at(8)),
    ]
    body = _forecast(client, readings=readings).json()
    assert body["forecast_status"] == "unavailable"
    assert body["projected_cycle_kwh"]["value"] is None
    assert body["average_daily_kwh"]["value"] is None
    assert "register decrease" in " ".join(body["missing_inputs"])


def test_other_meter_readings_are_not_mixed_in(client: TestClient) -> None:
    readings = [
        *_series(),
        _reading("1.000", _at(1), "MTR-2002"),
        _reading("50.000", _at(8), "MTR-2002"),
    ]
    body = _forecast(client, readings=readings).json()
    assert body["projected_cycle_kwh"]["value"] == "140.000"
    alone = _forecast(client, meter_reference="MTR-2002", readings=readings).json()
    assert alone["forecast_status"] == "unavailable"


def test_no_remaining_days_does_not_produce_a_negative_forecast(client: TestClient) -> None:
    ended = _forecast(client, as_of="2026-11-15T00:00:00Z").json()
    past = _forecast(client, as_of="2026-11-16T00:00:00Z").json()
    assert ended["projected_additional_kwh"]["value"] is None
    assert past["projected_additional_kwh"]["value"] is None
    assert ended["forecast_status"] == "unavailable"
    assert "No days remain" in " ".join(ended["missing_inputs"])


def test_invalid_precision_is_rejected(client: TestClient) -> None:
    response = _forecast(client, cycle_start_register_kwh="1.2345")
    assert response.status_code == 422


def test_production_tariff_does_not_create_a_payable_forecast(client: TestClient) -> None:
    body = _forecast(
        client,
        monthly_budget_pkr="8000.00",
        monthly_kwh_target="180.000",
        provider_code="IESCO",
        consumer_category="residential",
        tariff_type="non_tou",
        eligibility="unprotected",
        billing_date="2026-11-08",
    ).json()
    assert body["forecast_status"] == "estimated"
    assert body["bill_cost"]["value"] is None
    assert body["bill_cost"]["trust_status"] == "Unavailable"
    assert body["bill_cost"]["comparable_with_budget"] is False
    assert "GST" in body["bill_cost"]["missing_components"]
    assert "Fuel price adjustment" in body["bill_cost"]["missing_components"]
    assert body["budget_comparison"]["value"] is None
    assert body["budget_comparison"]["comparable_with_budget"] is False
    assert "cannot be compared" in body["budget_comparison"]["reason"]
    assert body["target_comparison"]["direction"] == "lower"
    assert body["target_comparison"]["trust_status"] == "Estimated"
    assert "8000" not in str(body["bill_cost"])
    assert body["monthly_budget_pkr"] == "8000.00"


def test_budget_validation_rejects_empty_zero_and_unreasonable_amounts(client: TestClient) -> None:
    empty = client.post("/api/predictions/budget", json={})
    zero = client.post("/api/predictions/budget", json={"monthly_budget_pkr": "0.00"})
    negative = client.post("/api/predictions/budget", json={"monthly_budget_pkr": "-1.00"})
    huge = client.post("/api/predictions/budget", json={"monthly_budget_pkr": "1000000.01"})
    malformed = client.post("/api/predictions/budget", json={"monthly_kwh_target": "1e2"})
    assert empty.status_code == 422
    assert zero.status_code == 422
    assert negative.status_code == 422
    assert huge.status_code == 422
    assert malformed.status_code == 422
    valid = client.post(
        "/api/predictions/budget",
        json={"monthly_budget_pkr": "1500.50", "monthly_kwh_target": "180.500"},
    )
    assert valid.status_code == 200
    assert valid.json()["monthly_budget_pkr"] == "1500.50"
    assert valid.json()["storage"] == "browser_only"
    assert "Another device" in valid.json()["limitation"]


def test_forecast_is_not_retained(client: TestClient) -> None:
    first = _forecast(client).json()
    assert first["storage"] == "not_retained"
    second = client.post("/api/predictions/consumption", json={"as_of": _at(7).isoformat()}).json()
    assert second["forecast_status"] == "unavailable"
    assert second["projected_cycle_kwh"]["value"] is None
