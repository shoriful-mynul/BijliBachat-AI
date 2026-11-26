from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

METER = "MTR-1001"
OTHER = "MTR-2002"
START = "11111111-1111-4111-8111-111111111111"
END = "22222222-2222-4222-8222-222222222222"
CYCLE = "33333333-3333-4333-8333-333333333333"


def _at(day: int, month: int = 1) -> str:
    return (datetime(2026, month, 1, tzinfo=timezone.utc) + timedelta(days=day)).isoformat()


def _checkpoint(checkpoint_id: str, register: str, when: str, meter: str = METER, confirmed: bool = True) -> dict:
    return {
        "id": checkpoint_id,
        "register_kwh": register,
        "read_at": when,
        "meter_reference": meter,
        "confirmed": confirmed,
    }


def _cycle(cycle_id: str, started: str, ended: str, start_register: str, end_register: str, meter: str = METER) -> dict:
    return {
        "id": cycle_id,
        "meter_reference": meter,
        "start_checkpoint_id": str(uuid4()),
        "end_checkpoint_id": str(uuid4()),
        "started_at": started,
        "ended_at": ended,
        "start_register_kwh": start_register,
        "end_register_kwh": end_register,
    }


def _validate(client: TestClient, **overrides: object):
    start = _checkpoint(START, "100.000", _at(0))
    end = _checkpoint(END, "250.000", _at(30))
    body: dict[str, object] = {
        "cycle_id": CYCLE,
        "start_checkpoint_id": START,
        "end_checkpoint_id": END,
        "readings": [start, end],
    }
    body.update(overrides)
    return client.post("/api/history/cycles/validate", json=body)


def test_valid_cycle_uses_register_difference(client: TestClient) -> None:
    body = _validate(client).json()
    assert body["status"] == "accepted"
    assert body["cycle"]["actual_kwh"] == "150.000"
    assert body["cycle"]["duration_days"] == "30.000"
    assert body["cycle"]["average_daily_kwh"] == "5.000"
    assert body["cycle"]["trust_status"] == "Calculated"
    assert body["storage"] == "not_retained"
    assert body["pkr_impact"]["value"] is None


def test_checkpoints_must_match_and_move_forward(client: TestClient) -> None:
    missing = _validate(client, readings=[_checkpoint(START, "100.000", _at(0))]).json()
    different = _validate(
        client,
        readings=[
            _checkpoint(START, "100.000", _at(0), METER),
            _checkpoint(END, "250.000", _at(30), OTHER),
        ],
    ).json()
    reversed_time = _validate(
        client,
        readings=[
            _checkpoint(START, "100.000", _at(30)),
            _checkpoint(END, "250.000", _at(0)),
        ],
    ).json()
    decreased = _validate(
        client,
        readings=[
            _checkpoint(START, "250.000", _at(0)),
            _checkpoint(END, "100.000", _at(30)),
        ],
    ).json()
    assert missing["status"] == "unavailable"
    assert different["status"] == "rejected"
    assert "same recorded meter" in different["detail"]
    assert reversed_time["status"] == "rejected"
    assert decreased["status"] == "rejected"
    assert decreased["cycle"] is None


def test_unconfirmed_checkpoint_is_rejected(client: TestClient) -> None:
    response = _validate(
        client,
        readings=[
            _checkpoint(START, "100.000", _at(0)),
            _checkpoint(END, "250.000", _at(30), confirmed=False),
        ],
    )
    assert response.status_code == 422


def test_duplicate_and_overlapping_cycles_are_rejected(client: TestClient) -> None:
    existing = {
        "id": "44444444-4444-4444-8444-444444444444",
        "meter_reference": METER,
        "start_checkpoint_id": START,
        "end_checkpoint_id": END,
        "started_at": _at(0),
        "ended_at": _at(30),
    }
    duplicate = _validate(client, existing_cycles=[existing]).json()
    overlap = _validate(
        client,
        start_checkpoint_id="55555555-5555-4555-8555-555555555555",
        end_checkpoint_id="66666666-6666-4666-8666-666666666666",
        readings=[
            _checkpoint("55555555-5555-4555-8555-555555555555", "200.000", _at(10)),
            _checkpoint("66666666-6666-4666-8666-666666666666", "280.000", _at(40)),
        ],
        existing_cycles=[existing],
    ).json()
    touching = _validate(
        client,
        cycle_id="77777777-7777-4777-8777-777777777777",
        start_checkpoint_id=END,
        end_checkpoint_id="88888888-8888-4888-8888-888888888888",
        readings=[
            _checkpoint(END, "250.000", _at(30)),
            _checkpoint("88888888-8888-4888-8888-888888888888", "300.000", _at(60)),
        ],
        existing_cycles=[existing],
    ).json()
    assert "already a cycle" in duplicate["detail"]
    assert "overlaps" in overlap["detail"]
    assert touching["status"] == "accepted"


def test_same_duration_comparison_and_average(client: TestClient) -> None:
    earlier = _cycle(CYCLE, _at(0), _at(30), "100.000", "250.000")
    later = _cycle("99999999-9999-4999-8999-999999999999", _at(30), _at(60), "250.000", "370.000")
    body = client.post("/api/history/cycles/compare", json={"earlier": earlier, "later": later}).json()
    assert body["status"] == "calculated"
    assert body["durations_comparable"] is True
    assert body["duration_warning"] is None
    assert body["earlier"]["actual_kwh"] == "150.000"
    assert body["later"]["actual_kwh"] == "120.000"
    assert body["usage_difference_kwh"] == "30.000"
    assert body["direction"] == "reduced"
    assert body["average_daily_difference_kwh"] == "1.000"
    assert body["percentage_difference"] == "20.00"
    assert "lower than the previous cycle" in body["detail"]
    assert "caused" in body["detail"]


def test_different_durations_warn_and_prefer_daily_average(client: TestClient) -> None:
    earlier = _cycle(CYCLE, _at(0), _at(10), "100.000", "140.000")
    later_end = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=40)).isoformat()
    later = _cycle("99999999-9999-4999-8999-999999999999", _at(10), later_end, "140.000", "290.000")
    body = client.post("/api/history/cycles/compare", json={"earlier": earlier, "later": later}).json()
    assert body["durations_comparable"] is False
    assert body["duration_warning"]
    assert body["earlier"]["actual_kwh"] == "40.000"
    assert body["later"]["actual_kwh"] == "150.000"
    assert body["direction"] == "increased"
    assert body["percentage_difference"] == "-25.00"
    assert "like-for-like" in body["duration_warning"]


def test_different_meters_are_not_compared(client: TestClient) -> None:
    earlier = _cycle(CYCLE, _at(0), _at(30), "100.000", "250.000", METER)
    later = _cycle("99999999-9999-4999-8999-999999999999", _at(30), _at(60), "10.000", "20.000", OTHER)
    body = client.post("/api/history/cycles/compare", json={"earlier": earlier, "later": later}).json()
    assert body["status"] == "unavailable"
    assert body["usage_difference_kwh"] is None
    assert "same meter" in body["detail"]


def test_average_rounds_half_up_after_the_exact_division(client: TestClient) -> None:
    cycle = _cycle(CYCLE, _at(0), _at(6), "0.000", "1.000")
    body = client.post(
        "/api/history/cycles/compare",
        json={"earlier": cycle, "later": _cycle("99999999-9999-4999-8999-999999999999", _at(6), _at(12), "1.000", "2.000")},
    ).json()
    assert body["earlier"]["average_daily_kwh"] == "0.167"
    assert body["direction"] == "unchanged"


def test_forecast_snapshot_copies_an_estimated_forecast_and_skips_an_unavailable_one(client: TestClient) -> None:
    series = [
        {
            "id": str(uuid4()),
            "register_kwh": register,
            "read_at": when,
            "meter_reference": METER,
            "capture_method": "manual",
            "trust_status": "Verified",
        }
        for register, when in (
            ("100.000", _at(0, 11)),
            ("130.000", _at(3, 11)),
            ("170.000", _at(7, 11)),
        )
    ]
    snapshot_id = str(uuid4())
    saved = client.post(
        "/api/history/forecast-snapshots",
        json={
            "snapshot_id": snapshot_id,
            "as_of": _at(7, 11),
            "meter_reference": METER,
            "readings": series,
            "cycle_started_on": "2026-11-01",
            "cycle_ends_on": "2026-11-15",
            "cycle_start_register_kwh": "100.000",
        },
    ).json()
    direct = client.post(
        "/api/predictions/consumption",
        json={
            "as_of": _at(7, 11),
            "meter_reference": METER,
            "readings": series,
            "cycle_started_on": "2026-11-01",
            "cycle_ends_on": "2026-11-15",
            "cycle_start_register_kwh": "100.000",
        },
    ).json()
    assert saved["status"] == "estimated"
    assert saved["snapshot"]["projected_cycle_kwh"] == direct["projected_cycle_kwh"]["value"]
    assert saved["snapshot"]["trust_status"] == "Estimated"
    assert saved["snapshot"]["method"] == "checkpoint-pace-v1"
    assert saved["storage"] == "not_retained"
    blocked = client.post(
        "/api/history/forecast-snapshots",
        json={
            "snapshot_id": str(uuid4()),
            "as_of": _at(7, 11),
            "meter_reference": METER,
            "readings": series[:1],
            "cycle_started_on": "2026-11-01",
            "cycle_ends_on": "2026-11-15",
            "cycle_start_register_kwh": "100.000",
        },
    ).json()
    assert blocked["status"] == "unavailable"
    assert blocked["snapshot"] is None


def test_forecast_comparison_above_below_and_zero_baseline(client: TestClient) -> None:
    cycle = _cycle(CYCLE, "2026-11-01T00:00:00+00:00", "2026-11-15T00:00:00+00:00", "100.000", "250.000")
    snapshot = _snapshot("140.000")
    above = client.post("/api/history/forecast-comparisons", json={"snapshot": snapshot, "cycle": cycle}).json()
    below_cycle = _cycle(CYCLE, "2026-11-01T00:00:00+00:00", "2026-11-15T00:00:00+00:00", "100.000", "180.000")
    below = client.post("/api/history/forecast-comparisons", json={"snapshot": snapshot, "cycle": below_cycle}).json()
    zero = _snapshot("0.000", start_register="0.000")
    zero_body = client.post(
        "/api/history/forecast-comparisons",
        json={"snapshot": zero, "cycle": _cycle(CYCLE, "2026-11-01T00:00:00+00:00", "2026-11-15T00:00:00+00:00", "0.000", "5.000")},
    ).json()
    assert above["direction"] == "higher"
    assert above["actual_kwh"] == "150.000"
    assert above["forecast_kwh"] == "140.000"
    assert above["difference_kwh"] == "10.000"
    assert above["actual_trust_status"] == "Calculated"
    assert above["forecast_trust_status"] == "Estimated"
    assert above["difference_trust_status"] == "Calculated"
    assert "accuracy guarantee" in above["detail"]
    assert below["direction"] == "lower"
    assert below["actual_kwh"] == "80.000"
    assert below["difference_kwh"] == "-60.000"
    assert below["absolute_difference_kwh"] == "60.000"
    assert below["percentage_difference"] == "-42.86"
    assert zero_body["percentage_difference"] is None
    assert zero_body["direction"] == "higher"
    assert zero_body["pkr_impact"]["value"] is None


def test_percentage_uses_exact_ratio_before_display_rounding(client: TestClient) -> None:
    cycle = _cycle(CYCLE, "2026-11-01T00:00:00+00:00", "2026-11-15T00:00:00+00:00", "0.000", "1.000")
    body = client.post(
        "/api/history/forecast-comparisons",
        json={"snapshot": _snapshot("3.000", start_register="0.000"), "cycle": cycle},
    ).json()
    assert body["difference_kwh"] == "-2.000"
    assert body["percentage_difference"] == "-66.67"
    assert body["direction"] == "lower"


def test_user_target_is_not_a_verified_baseline(client: TestClient) -> None:
    cycle = _cycle(CYCLE, _at(0), _at(30), "0.000", "142.000")
    body = client.post(
        "/api/history/baseline-comparisons",
        json={"cycle": cycle, "cycle_id": CYCLE, "target_kwh": "150.000"},
    ).json()
    assert body["status"] == "calculated"
    assert body["direction"] == "lower"
    assert body["input_source"] == "entered_by_household"
    assert "Your entered target was 150.000 kWh; measured consumption was 142.000 kWh." in body["detail"]
    assert "not a rupee saving" in body["detail"]
    assert body["trust_status"] == "Calculated"
    mismatch = client.post(
        "/api/history/baseline-comparisons",
        json={"cycle": cycle, "cycle_id": "99999999-9999-4999-8999-999999999999", "target_kwh": "150.000"},
    ).json()
    assert mismatch["status"] == "unavailable"


def test_insights_need_two_cycles_from_the_same_meter(client: TestClient) -> None:
    one = _cycle(CYCLE, _at(0), _at(30), "100.000", "250.000")
    empty = client.post("/api/history/insights", json={"cycles": []}).json()
    single = client.post("/api/history/insights", json={"cycles": [one]}).json()
    other = _cycle("99999999-9999-4999-8999-999999999999", _at(30), _at(60), "1.000", "2.000", OTHER)
    mismatch = client.post("/api/history/insights", json={"cycles": [one, other]}).json()
    later = _cycle("99999999-9999-4999-8999-999999999999", _at(30), _at(60), "250.000", "370.000")
    trend = client.post("/api/history/insights", json={"cycles": [one, later]}).json()
    assert empty["insights"][0]["code"] == "insufficient"
    assert single["latest_cycle_kwh"] == "150.000"
    assert single["direction"] == "unavailable"
    assert mismatch["insights"][0]["code"] == "meter_mismatch"
    assert trend["direction"] == "reduced"
    assert trend["insights"][0]["trust_status"] == "Calculated"


def test_malformed_numbers_and_no_rupee_figure(client: TestClient) -> None:
    response = _validate(client, readings=[_checkpoint(START, "1e2", _at(0)), _checkpoint(END, "250.000", _at(30))])
    assert response.status_code == 422
    body = _validate(client).json()
    assert "GST" in body["pkr_impact"]["missing_components"]
    assert "0.00" not in str(body["pkr_impact"])
    assert body["pkr_impact"]["comparable"] is False


def test_results_are_not_retained(client: TestClient) -> None:
    first = _validate(client).json()
    second = client.post("/api/history/insights", json={"cycles": []}).json()
    assert first["cycle"]["actual_kwh"] == "150.000"
    assert second["cycle_count"] == 0


def _snapshot(projected: str, start_register: str = "100.000") -> dict:
    return {
        "id": str(uuid4()),
        "meter_reference": METER,
        "created_at": "2026-11-08T00:00:00+00:00",
        "cycle_started_on": "2026-11-01",
        "cycle_ends_on": "2026-11-15",
        "cycle_start_register_kwh": start_register,
        "latest_register_kwh": "170.000",
        "latest_checkpoint_id": str(uuid4()),
        "projected_cycle_kwh": projected,
        "reading_ids": [str(uuid4())],
        "trust_status": "Estimated",
        "method": "checkpoint-pace-v1",
    }
