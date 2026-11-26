from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.integrations.gemini.errors import GeminiNotConfigured, GeminiSchemaError, GeminiTimeout, GeminiUnavailable
from app.repositories.meter_ledger import ProcessLocalLedger
from app.services.bill_files import clear_upload_buffer
from tests.bill_samples import JPEG, PDF, PNG

HOUSEHOLD = "3b1f2a44-0c3e-4d5b-8e7f-1a2b3c4d5e6f"


class FakeMeterExtractor:
    def __init__(self, payload: object | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {
            "reading_kwh": {"value": "15482.5", "confidence": "readable", "note": None},
            "unit_label": {"value": "kWh", "confidence": "readable", "note": None},
            "meter_reference": {"value": "MTR-1001", "confidence": "readable", "note": None},
        }
        self.error = error
        self.calls = 0

    def extract_meter_photo(self, content: bytes, mime_type: str) -> dict:
        self.calls += 1
        if self.error:
            raise self.error
        if not isinstance(self.payload, dict):
            raise GeminiSchemaError()
        return self.payload


def _use(client: TestClient, extractor: FakeMeterExtractor | None = None) -> FakeMeterExtractor:
    fake = extractor or FakeMeterExtractor()
    client.app.state.meter_extractor = fake
    return fake


def _upload(client: TestClient, content: bytes, mime: str):
    return client.post("/api/meter-readings/extractions", files={"file": ("meter.png", content, mime)})


def _reading(register: str, when: str, **overrides: object) -> dict:
    body = {
        "confirmation": "user_confirmed",
        "register_kwh": register,
        "read_at": when,
        "capture_method": "manual",
        "meter_reference": "MTR-1001",
        "origin": "manual",
    }
    body.update(overrides)
    return body


def _submit(client: TestClient, reading: dict, prior: list | None = None):
    return client.post(
        "/api/meter-readings",
        json={"household_id": HOUSEHOLD, "reading": reading, "prior_readings": prior or []},
    )


def _prior(register: str, when: str, reference: str = "MTR-1001") -> dict:
    return {
        "id": str(uuid4()),
        "register_kwh": register,
        "read_at": when,
        "meter_reference": reference,
        "capture_method": "manual",
        "trust_status": "Verified",
    }


def test_manual_reading_is_confirmed_and_not_retained(client: TestClient) -> None:
    response = _submit(client, _reading("100.000", "2026-11-01T00:00:00Z"))

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["checkpoint"]["register_kwh"] == "100.000"
    assert body["checkpoint"]["confirmation_state"] == "confirmed"
    assert body["checkpoint"]["trust_status"] == "Verified"
    assert body["storage"] == "not_retained"
    listed = client.get("/api/meter-readings", params={"household_id": HOUSEHOLD})
    assert listed.status_code == 200
    assert listed.json()["readings"] == []
    assert "another device" in listed.json()["limitation"]


def test_process_local_ledger_is_not_the_api_default(client: TestClient) -> None:
    ledger = ProcessLocalLedger()
    client.app.state.meter_ledger = ledger
    response = _submit(client, _reading("10.000", "2026-11-01T00:00:00Z"))
    assert response.status_code == 200
    assert len(ledger.items) == 1
    listed = client.get("/api/meter-readings", params={"household_id": HOUSEHOLD})
    assert listed.json()["readings"][0]["register_kwh"] == "10.000"


def test_consecutive_consumption_and_a_different_meter(client: TestClient) -> None:
    first = _prior("100.000", "2026-11-01T00:00:00Z")
    second = _submit(client, _reading("130.000", "2026-11-04T00:00:00Z"), [first])
    assert second.json()["accepted"] is True
    other = _submit(
        client,
        _reading("5.000", "2026-11-02T00:00:00Z", meter_reference="MTR-2002"),
        [first],
    )
    assert other.json()["accepted"] is True
    cliff = client.post(
        "/api/cliff-guard",
        json={
            "as_of": "2026-11-04T00:00:00Z",
            "meter_reference": "MTR-1001",
            "readings": [first, _prior("130.000", "2026-11-04T00:00:00Z")],
        },
    )
    body = cliff.json()
    assert body["consumption_kwh"]["value"] == "30.000"
    assert body["consumption_kwh"]["trust_status"] == "Calculated"
    assert body["average_daily_kwh"]["value"] == "10.000"
    assert body["observation_period"] == "2026-11-01 to 2026-11-04"
    assert "not a live meter feed" in body["limitations"][0]


def test_duplicate_out_of_order_and_decrease_are_not_silently_accepted(client: TestClient) -> None:
    prior = _prior("100.000", "2026-11-04T00:00:00Z")
    duplicate = _submit(client, _reading("140.000", "2026-11-04T00:00:00Z"), [prior])
    assert duplicate.json()["outcome"] == "rejected"
    older = _submit(client, _reading("140.000", "2026-11-02T00:00:00Z"), [prior])
    assert older.json()["outcome"] == "rejected"
    lower = _submit(client, _reading("90.000", "2026-11-05T00:00:00Z"), [prior])
    assert lower.json()["outcome"] == "needs_review"
    assert lower.json()["accepted"] is False
    assert "90.000" not in lower.json()["explanation"] or "lower" in lower.json()["explanation"]
    kept = _submit(
        client,
        _reading("90.000", "2026-11-05T00:00:00Z", review_decision="keep_as_submitted"),
        [prior],
    )
    assert kept.json()["accepted"] is True
    assert kept.json()["checkpoint"]["register_kwh"] == "90.000"


def test_zero_elapsed_time_does_not_average(client: TestClient) -> None:
    same = "2026-11-04T00:00:00Z"
    response = client.post(
        "/api/cliff-guard",
        json={
            "as_of": same,
            "meter_reference": "MTR-1001",
            "readings": [_prior("100.000", same), _prior("110.000", same)],
        },
    )
    body = response.json()
    assert body["average_daily_kwh"]["value"] is None
    assert body["average_daily_kwh"]["trust_status"] == "Unavailable"


def test_invalid_precision_and_naive_date_are_rejected(client: TestClient) -> None:
    precise = _submit(client, _reading("1.2345", "2026-11-01T00:00:00Z"))
    naive = _submit(client, _reading("10", "2026-11-01T00:00:00"))
    assert precise.status_code == 422
    assert naive.status_code == 422


def test_possible_reading_anomaly_does_not_change_the_register(client: TestClient) -> None:
    priors = [
        _prior("0.000", "2026-11-01T00:00:00Z"),
        _prior("10.000", "2026-11-03T00:00:00Z"),
    ]
    response = _submit(client, _reading("100.000", "2026-11-05T00:00:00Z"), priors)
    body = response.json()
    assert body["outcome"] == "needs_review"
    assert "Possible reading anomaly" in body["explanation"]
    assert "fraud" not in body["explanation"].lower()
    assert body["checkpoint"] is None


def test_photo_extraction_stays_unconfirmed_and_cleans_the_buffer(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    cleared: list[int] = []

    def spy(buffer: bytearray) -> None:
        cleared.append(len(buffer))
        clear_upload_buffer(buffer)

    monkeypatch.setattr("app.api.routes.meter.clear_upload_buffer", spy)
    _use(client, FakeMeterExtractor())
    response = _upload(client, PNG, "image/png")
    assert response.status_code == 200
    body = response.json()
    assert body["confirmed"] is False
    assert body["reading_kwh"]["value"] == "15482.500"
    assert body["reading_kwh"]["trust_status"] == "Extracted"
    _use(client, FakeMeterExtractor(error=GeminiUnavailable()))
    assert _upload(client, JPEG, "image/jpeg").status_code == 503
    assert cleared == [len(PNG), len(JPEG)]


def test_unreadable_meter_digit_is_not_zero(client: TestClient) -> None:
    _use(
        client,
        FakeMeterExtractor(
            {
                "reading_kwh": {"value": "0", "confidence": "unreadable", "note": "The last digit is blurred."},
                "unit_label": {"value": None, "confidence": "missing", "note": None},
                "meter_reference": {"value": None, "confidence": "missing", "note": None},
            }
        ),
    )
    body = _upload(client, PNG, "image/png").json()
    assert body["reading_kwh"]["value"] is None
    assert body["reading_kwh"]["trust_status"] == "Unavailable"
    assert body["requires_manual_review"] is True
    assert body["confirmed"] is False


def test_meter_file_rejections_and_missing_gemini(client: TestClient) -> None:
    _use(client)
    assert _upload(client, b"", "image/png").status_code == 400
    assert _upload(client, PDF, "application/pdf").status_code == 400
    assert _upload(client, PNG, "image/jpeg").status_code == 400
    assert _upload(client, b"\x00" * (8 * 1024 * 1024 + 1), "application/octet-stream").status_code == 400
    client.app.state.meter_extractor = None
    missing = _upload(client, PNG, "image/png")
    assert missing.status_code == 503
    assert "not configured" in missing.json()["message"]


@pytest.mark.parametrize("error", [GeminiNotConfigured(), GeminiTimeout(), GeminiSchemaError()])
def test_meter_gemini_failures_do_not_invent_a_reading(client: TestClient, error: Exception) -> None:
    _use(client, FakeMeterExtractor(error=error))
    response = _upload(client, PNG, "image/png")
    assert response.status_code == 503
    assert "15482" not in response.text


def test_corrected_photo_value_is_the_value_that_is_validated(client: TestClient) -> None:
    _use(client)
    extracted = _upload(client, PNG, "image/png").json()
    assert extracted["confirmed"] is False
    saved = _submit(
        client,
        _reading("20.000", "2026-11-02T00:00:00Z", capture_method="photo", origin="photo_corrected"),
    )
    assert saved.json()["checkpoint"]["register_kwh"] == "20.000"
    assert saved.json()["checkpoint"]["trust_status"] == "Verified"
    unchanged = _submit(
        client,
        _reading("21.000", "2026-11-03T00:00:00Z", capture_method="photo", origin="photo_confirmed"),
    )
    assert unchanged.json()["checkpoint"]["trust_status"] == "Extracted"


def test_cliff_guard_has_no_verified_threshold_and_no_negative_allowance(client: TestClient) -> None:
    empty = client.get("/api/cliff-guard")
    assert empty.status_code == 200
    assert empty.json()["threshold_kwh"] is None
    assert empty.json()["consumption_kwh"]["value"] is None
    assert empty.json()["safe_daily_allowance_kwh"]["value"] is None
    scoped = client.post(
        "/api/cliff-guard",
        json={
            "as_of": "2026-11-20T00:00:00Z",
            "meter_reference": "MTR-1001",
            "readings": [
                _prior("1000.000", "2026-11-01T00:00:00Z"),
                _prior("1120.000", "2026-11-10T00:00:00Z"),
                _prior("1240.000", "2026-11-20T00:00:00Z"),
            ],
            "provider_code": "IESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-11-20",
            "cycle_started_on": "2026-11-01",
            "cycle_ends_on": "2026-11-30",
            "cycle_start_register_kwh": "1000.000",
        },
    )
    body = scoped.json()
    assert body["threshold_status"] == "needs_verification"
    assert body["threshold_kwh"] is None
    assert body["billing_cycle_consumption_kwh"]["value"] == "240.000"
    assert body["remaining_kwh"]["value"] is None
    assert body["safe_daily_allowance_kwh"]["value"] is None
    assert body["projection"]["message"] == "Threshold needs verification for this tariff configuration."
    assert body["projection"]["projected_date"] is None
    assert "200" not in body["threshold_source"]
    joined = str(body)
    assert "fraud" not in joined.lower()


def test_short_history_names_the_projection_limit(client: TestClient) -> None:
    response = client.post(
        "/api/cliff-guard",
        json={
            "as_of": "2026-11-04T00:00:00Z",
            "readings": [_prior("10.000", "2026-11-01T00:00:00Z"), _prior("16.000", "2026-11-04T00:00:00Z")],
        },
    )
    assert response.json()["projection"]["message"] == "Not enough reading history for a reliable projection."


def test_billing_cycle_does_not_use_an_arbitrary_earlier_reading(client: TestClient) -> None:
    response = client.post(
        "/api/cliff-guard",
        json={
            "as_of": "2026-11-10T00:00:00Z",
            "readings": [_prior("50.000", "2026-10-01T00:00:00Z"), _prior("80.000", "2026-11-10T00:00:00Z")],
        },
    )
    cycle = response.json()["billing_cycle_consumption_kwh"]
    assert cycle["value"] is None
    assert "explicit" in cycle["detail"]


def test_allowance_formula_does_not_return_a_negative_recommendation() -> None:
    from decimal import Decimal

    from app.services.cliff_guard import safe_daily_allowance

    assert safe_daily_allowance(Decimal("30"), Decimal("10")) == Decimal("3.000")
    assert safe_daily_allowance(Decimal("-1"), Decimal("10")) is None
    assert safe_daily_allowance(Decimal("10"), Decimal("0")) is None


def test_openapi_still_hides_the_domain_meter_schema(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "MeterReading" not in schemas
    assert "HouseholdProfile" not in schemas
