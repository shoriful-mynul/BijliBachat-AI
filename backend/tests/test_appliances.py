from uuid import uuid4

from fastapi.testclient import TestClient

FAN = "6b9c1d20-7e44-4a1b-9c30-2f6a8b0c1d11"
IRON = "7c0d2e31-8f55-4b2c-8d41-3a7b9c1d2e22"


def _appliance(name: str, watts: str, hours: str, quantity: int = 1, **extra: object) -> dict:
    body = {
        "id": extra.pop("id", str(uuid4())),
        "name": name,
        "rated_watts": watts,
        "quantity": quantity,
        "operating_hours_per_day": hours,
    }
    body.update(extra)
    return body


def _fan(**overrides: object) -> dict:
    body = _appliance("Ceiling fan", "75", "8", id=FAN)
    body.update(overrides)
    return body


def test_single_appliance_daily_and_period(client: TestClient) -> None:
    response = client.post(
        "/api/appliances/consumption",
        json={"appliances": [_fan()], "days": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "calculated"
    assert body["total_daily_kwh"] == "0.600"
    assert body["total_period_kwh"] == "6.000"
    assert body["appliances"][0]["trust_status"] == "Calculated"
    assert body["appliances"][0]["input_source"] == "entered_by_household"
    assert "Verified" not in body["appliances"][0]["detail"]
    assert body["pkr_impact"]["value"] is None


def test_multiple_appliances_and_quantity(client: TestClient) -> None:
    lights = _appliance("Bulb", "10", "5", quantity=4, id=IRON)
    response = client.post(
        "/api/appliances/consumption",
        json={"appliances": [_fan(), lights], "days": 2},
    )
    body = response.json()
    assert body["total_daily_kwh"] == "0.800"
    assert body["appliances"][1]["daily_kwh"] == "0.200"
    assert body["appliances"][0]["share_percent"] == "75.00"


def test_decimal_inputs_and_period_are_not_rounded_early(client: TestClient) -> None:
    appliance = _appliance("Clock", "1", "0.500", id=FAN)
    body = client.post(
        "/api/appliances/consumption",
        json={"appliances": [appliance], "days": 3},
    ).json()
    assert body["total_daily_kwh"] == "0.001"
    assert body["total_period_kwh"] == "0.002"


def test_invalid_wattage_quantity_and_hours_are_rejected(client: TestClient) -> None:
    cases = [
        _fan(rated_watts="0"),
        _fan(rated_watts="-5"),
        _fan(quantity=0),
        _fan(quantity=-1),
        _fan(operating_hours_per_day="24.001"),
        _fan(operating_hours_per_day="0"),
        _fan(rated_watts="1e2"),
        _fan(operating_hours_per_day="8.5e0"),
    ]
    for appliance in cases:
        response = client.post("/api/appliances/consumption", json={"appliances": [appliance]})
        assert response.status_code == 422


def test_missing_and_malformed_inputs(client: TestClient) -> None:
    incomplete = _fan()
    del incomplete["rated_watts"]
    missing = client.post("/api/appliances/consumption", json={"appliances": [incomplete]})
    malformed = client.post(
        "/api/appliances/consumption",
        json={"appliances": [_fan()], "days": "1e1"},
    )
    too_long = client.post("/api/appliances/consumption", json={"appliances": [_fan()], "days": 367})
    assert missing.status_code == 422
    assert malformed.status_code == 422
    assert too_long.status_code == 422


def test_days_are_not_assumed(client: TestClient) -> None:
    body = client.post("/api/appliances/consumption", json={"appliances": [_fan()]}).json()
    assert body["total_daily_kwh"] == "0.600"
    assert body["total_period_kwh"] is None
    assert "30-day month was not assumed" in " ".join(body["limitations"])


def test_reduced_increased_and_unchanged_scenarios(client: TestClient) -> None:
    baseline = _fan()
    less = _fan(operating_hours_per_day="4")
    more = _fan(operating_hours_per_day="10")
    same = _fan()
    reduced = client.post(
        "/api/appliances/scenarios",
        json={"baseline": [baseline], "proposed": [less], "days": 10},
    ).json()
    increased = client.post(
        "/api/appliances/scenarios",
        json={"baseline": [baseline], "proposed": [more], "days": 10},
    ).json()
    unchanged = client.post(
        "/api/appliances/scenarios",
        json={"baseline": [baseline], "proposed": [same], "days": 10},
    ).json()
    assert reduced["direction"] == "reduced"
    assert reduced["baseline_kwh"] == "6.000"
    assert reduced["scenario_kwh"] == "3.000"
    assert reduced["difference_kwh"] == "3.000"
    assert reduced["percentage_difference"] == "50.00"
    assert increased["direction"] == "increased"
    assert increased["difference_kwh"] == "1.500"
    assert increased["percentage_difference"] == "-25.00"
    assert "more" in increased["appliances"][0]["detail"]
    assert "less" not in increased["appliances"][0]["detail"]
    assert unchanged["direction"] == "unchanged"
    assert unchanged["difference_kwh"] == "0.000"
    assert unchanged["percentage_difference"] == "0.00"


def test_zero_baseline_has_no_percentage(client: TestClient) -> None:
    body = client.post(
        "/api/appliances/scenarios",
        json={"baseline": [], "proposed": [], "days": 7},
    ).json()
    assert body["status"] == "unavailable"
    assert body["percentage_difference"] is None
    assert body["baseline_kwh"] is None


def test_action_plan_uses_only_the_entered_change(client: TestClient) -> None:
    baseline = [_fan(), _appliance("Iron", "1000", "0.5", id=IRON)]
    proposed = [_fan(operating_hours_per_day="6"), _appliance("Iron", "1000", "0.5", id=IRON)]
    plan = client.post(
        "/api/appliances/action-plan",
        json={"baseline": baseline, "proposed": proposed, "days": 7},
    ).json()
    assert plan["status"] == "estimated"
    assert len(plan["actions"]) == 1
    assert plan["actions"][0]["appliance_name"] == "Ceiling fan"
    assert plan["actions"][0]["trust_status"] == "Estimated"
    assert "measured saving" in plan["actions"][0]["explanation"]
    same = client.post(
        "/api/appliances/action-plan",
        json={"baseline": baseline, "proposed": baseline, "days": 7},
    ).json()
    assert same["status"] == "unavailable"
    assert same["actions"] == []


def test_no_rupee_saving_is_fabricated(client: TestClient) -> None:
    body = client.post(
        "/api/appliances/scenarios",
        json={"baseline": [_fan()], "proposed": [_fan(operating_hours_per_day="4")], "days": 10},
    ).json()
    assert body["pkr_impact"]["value"] is None
    assert body["pkr_impact"]["trust_status"] == "Unavailable"
    assert body["pkr_impact"]["comparable"] is False
    assert "GST" in body["pkr_impact"]["missing_components"]
    assert "Fuel price adjustment" in body["pkr_impact"]["missing_components"]
    joined = str(body["pkr_impact"])
    assert "0.00" not in joined


def test_requests_are_not_retained(client: TestClient) -> None:
    first = client.post("/api/appliances/consumption", json={"appliances": [_fan()], "days": 1}).json()
    second = client.post("/api/appliances/consumption", json={"appliances": []}).json()
    assert first["storage"] == "not_retained"
    assert second["status"] == "unavailable"
    assert second["appliances"] == []


def test_scenario_rejects_a_different_appliance_set(client: TestClient) -> None:
    response = client.post(
        "/api/appliances/scenarios",
        json={"baseline": [_fan()], "proposed": [_appliance("Iron", "1000", "1", id=IRON)], "days": 1},
    )
    assert response.status_code == 422
