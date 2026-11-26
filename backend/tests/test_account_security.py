"""Account ownership tests. They use a fake verifier and never call Firebase."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.auth.identity import AuthenticatedUser
from app.auth.verifier import FakeTokenVerifier
from app.core.config import Settings
from app.main import create_app
from app.repositories.user_files import MemoryFileStore
from app.repositories.user_records import MemoryRecordStore, StoreError
from app.schemas.history import CycleInput
from app.services.history import _elapsed, _exact_actual, _q

HOUSEHOLD_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
METER_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
BILL_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
CYCLE_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
START_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff"
END_ID = "11111111-1111-4111-8111-111111111111"
SNAPSHOT_ID = "22222222-2222-4222-8222-222222222222"
APPLIANCE_ID = "33333333-3333-4333-8333-333333333333"

JPEG = b"\xff\xd8\xff" + b"\x00" * 16 + b"\xff\xd9"


def _household(record_id: str = HOUSEHOLD_ID, name: str = "Home") -> dict:
    return {
        "id": record_id,
        "display_name": name,
        "provider_code": "IESCO",
        "service_region": "Islamabad",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }


def _cycle() -> dict:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 31, tzinfo=timezone.utc)
    model = CycleInput(
        id=CYCLE_ID,
        meter_reference="MTR-1001",
        start_checkpoint_id=START_ID,
        end_checkpoint_id=END_ID,
        started_at=start,
        ended_at=end,
        start_register_kwh=Decimal("100.000"),
        end_register_kwh=Decimal("250.000"),
    )
    actual = _exact_actual(model)
    elapsed = _elapsed(model)
    return {
        "id": CYCLE_ID,
        "meter_reference": "MTR-1001",
        "start_checkpoint_id": START_ID,
        "end_checkpoint_id": END_ID,
        "started_at": "2026-01-01T00:00:00Z",
        "ended_at": "2026-01-31T00:00:00Z",
        "start_register_kwh": "100.000",
        "end_register_kwh": "250.000",
        "actual_kwh": _q(actual),
        "duration_days": _q(elapsed),
        "average_daily_kwh": _q(actual / elapsed),
        "trust_status": "Calculated",
        "detail": "Measured use from confirmed checkpoints.",
    }


@pytest.fixture
def cloud():
    app = create_app(Settings(app_env="test", cors_origins=["http://localhost:3000"]))
    store = MemoryRecordStore()
    files = MemoryFileStore()
    app.state.token_verifier = FakeTokenVerifier(
        {
            "token-a": AuthenticatedUser(uid="user-a", email="a@example.com"),
            "token-b": AuthenticatedUser(uid="user-b", email="b@example.com"),
        },
        expired={"token-expired"},
    )
    app.state.record_store = store
    app.state.file_store = files
    with TestClient(app) as client:
        yield client, store, files


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_local_mode_does_not_pretend_to_save(client: TestClient) -> None:
    response = client.put(f"/api/account/records/household/{HOUSEHOLD_ID}", json=_household())

    assert response.status_code == 503
    assert response.json()["message"] == "Cloud accounts are not configured. Nothing was saved."
    assert "saved successfully" not in response.text.lower()


def test_missing_invalid_and_expired_tokens(cloud) -> None:
    client, _, _ = cloud
    path = f"/api/account/records/household/{HOUSEHOLD_ID}"

    missing = client.get(path)
    malformed = client.get(path, headers={"Authorization": "Token token-a"})
    empty = client.get(path, headers={"Authorization": "Bearer "})
    invalid = client.get(path, headers=_auth("not-a-token"))
    expired = client.get(path, headers=_auth("token-expired"))

    assert missing.status_code == 401
    assert missing.json()["message"] == "Sign in is required."
    assert malformed.status_code == 401
    assert empty.status_code == 401
    assert invalid.status_code == 401
    assert expired.status_code == 401
    assert "not-a-token" not in invalid.text
    assert "token-expired" not in expired.text
    assert "a@example.com" not in invalid.text


def test_uid_comes_from_the_token_and_a_body_uid_is_rejected(cloud) -> None:
    client, store, _ = cloud
    spoofed = _household()
    spoofed["owner_uid"] = "user-b"

    rejected = client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-a"),
        json=spoofed,
    )
    assert rejected.status_code == 400
    assert store.list("user-a", "household") == []
    assert store.list("user-b", "household") == []

    saved = client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-a"),
        json=_household(),
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "created"
    stored = store.get("user-a", "household", HOUSEHOLD_ID)
    assert stored is not None
    assert stored["owner_uid"] == "user-a"
    assert "owner_uid" not in saved.json()["record"]


def test_user_cannot_read_update_or_delete_another_users_record(cloud) -> None:
    client, store, _ = cloud
    created = client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-a"),
        json=_household(),
    )
    assert created.status_code == 200

    read = client.get(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-b"),
    )
    delete = client.delete(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-b"),
    )
    update = client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-b"),
        json=_household(name="Other home"),
    )

    assert read.status_code == 404
    assert delete.status_code == 404
    assert update.status_code == 200
    assert store.get("user-a", "household", HOUSEHOLD_ID)["display_name"] == "Home"
    assert store.get("user-b", "household", HOUSEHOLD_ID)["display_name"] == "Other home"
    assert store.get("user-b", "household", HOUSEHOLD_ID)["owner_uid"] == "user-b"


def test_existing_record_is_not_overwritten(cloud) -> None:
    client, store, _ = cloud
    headers = _auth("token-a")
    path = f"/api/account/records/household/{HOUSEHOLD_ID}"
    assert client.put(path, headers=headers, json=_household()).status_code == 200
    again = client.put(path, headers=headers, json=_household(name="Later name"))

    assert again.status_code == 200
    assert again.json()["status"] == "already_present"
    assert store.get("user-a", "household", HOUSEHOLD_ID)["display_name"] == "Home"


def test_public_routes_stay_open_when_accounts_are_enabled(cloud) -> None:
    client, _, _ = cloud
    health = client.get("/api/health")
    tariffs = client.get("/api/tariffs")

    assert health.status_code == 200
    assert tariffs.status_code == 200
    assert health.json()["checks"][1]["name"] == "firebase"


def test_failed_write_is_not_reported_as_success(cloud) -> None:
    client, store, _ = cloud
    store.fail_puts = True
    response = client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-a"),
        json=_household(),
    )

    assert response.status_code == 503
    assert response.json()["message"] == "The record was not saved."
    assert store.get("user-a", "household", HOUSEHOLD_ID) is None


def test_internal_store_failure_hides_exception_text(cloud) -> None:
    client, store, _ = cloud

    def explode(*_args, **_kwargs):
        raise RuntimeError("BEGIN PRIVATE KEY")

    store.put = explode  # type: ignore[method-assign]
    response = client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=_auth("token-a"),
        json=_household(),
    )

    assert response.status_code == 503
    assert "PRIVATE KEY" not in response.text
    assert "Traceback" not in response.text


def test_unconfirmed_bill_and_meter_drafts_are_not_stored(cloud) -> None:
    client, store, _ = cloud
    headers = _auth("token-a")
    bill = client.put(
        f"/api/account/records/bill_audits/{BILL_ID}",
        headers=headers,
        json={"id": BILL_ID, "confirmed": False, "provider_code": "IESCO"},
    )
    meter = client.put(
        f"/api/account/records/meter_checkpoints/{METER_ID}",
        headers=headers,
        json={
            "id": METER_ID,
            "household_id": HOUSEHOLD_ID,
            "register_kwh": "10.000",
            "read_at": "2026-01-01T00:00:00Z",
            "capture_method": "photo",
            "confirmation_state": "pending_confirmation",
            "trust_status": "Extracted",
            "warnings": [],
        },
    )
    verified = client.put(
        f"/api/account/records/meter_checkpoints/{METER_ID}",
        headers=headers,
        json={
            "id": METER_ID,
            "household_id": HOUSEHOLD_ID,
            "register_kwh": "10.000",
            "read_at": "2026-01-01T00:00:00Z",
            "capture_method": "manual",
            "confirmation_state": "confirmed",
            "trust_status": "Verified",
            "warnings": [],
        },
    )

    assert bill.status_code == 400
    assert meter.status_code == 400
    assert verified.status_code == 400
    assert store.list("user-a", "bill_audits") == []
    assert store.list("user-a", "meter_checkpoints") == []


def test_confirmed_records_can_be_copied_without_replacing_existing_ones(cloud) -> None:
    client, store, _ = cloud
    headers = _auth("token-a")
    payload = {
        "household": [_household()],
        "meter_checkpoints": [
            {
                "id": METER_ID,
                "household_id": HOUSEHOLD_ID,
                "register_kwh": "10.000",
                "read_at": "2026-01-01T00:00:00Z",
                "meter_reference": "MTR-1001",
                "capture_method": "manual",
                "confirmation_state": "confirmed",
                "trust_status": "Calculated",
                "warnings": [],
            }
        ],
        "bill_audits": [
            {
                "id": BILL_ID,
                "saved_at": "2026-01-16T00:00:00Z",
                "confirmation": "user_confirmed",
                "bill": {
                    "confirmation": "user_confirmed",
                    "provider_code": "IESCO",
                    "consumer_category": "residential",
                    "tariff_type": "non_tou",
                    "billing_date": "2026-01-15",
                    "consumption_kwh": "100.000",
                },
            }
        ],
        "appliances": [
            {
                "id": APPLIANCE_ID,
                "name": "Fan",
                "rated_watts": "75",
                "quantity": 1,
                "operating_hours_per_day": "8",
            }
        ],
        "forecast_snapshots": [
            {
                "id": SNAPSHOT_ID,
                "created_at": "2026-01-10T00:00:00Z",
                "cycle_started_on": "2026-01-01",
                "cycle_ends_on": "2026-01-31",
                "cycle_start_register_kwh": "100.000",
                "latest_register_kwh": "150.000",
                "latest_checkpoint_id": METER_ID,
                "projected_cycle_kwh": "300.000",
                "reading_ids": [METER_ID],
                "assumptions": ["Pace from confirmed checkpoints."],
                "detail": "Estimated from the existing forecast.",
                "trust_status": "Estimated",
                "method": "checkpoint-pace-v1",
            }
        ],
        "history_cycles": [_cycle()],
        "history_baselines": [{"cycle_id": CYCLE_ID, "target_kwh": "200.000"}],
    }
    first = client.post("/api/account/import", headers=headers, json=payload)
    second = client.post("/api/account/import", headers=headers, json=payload)

    assert first.status_code == 200
    assert first.json()["continuous_synchronization"] is False
    assert first.json()["local_records_removed"] is False
    assert {item["status"] for item in first.json()["results"]} == {"created"}
    assert {item["status"] for item in second.json()["results"]} == {"already_present"}
    assert store.get("user-a", "household", HOUSEHOLD_ID)["owner_uid"] == "user-a"

    exported = client.get("/api/account/export", headers=_auth("token-b"))
    assert exported.status_code == 200
    assert exported.json()["records"]["household"] == []


def test_import_reports_a_rejected_record_and_keeps_the_valid_one(cloud) -> None:
    client, store, _ = cloud
    response = client.post(
        "/api/account/import",
        headers=_auth("token-a"),
        json={
            "household": [_household(), {"id": OTHER_ID, "display_name": ""}],
            "meter_checkpoints": [
                {
                    "id": METER_ID,
                    "confirmation_state": "pending_confirmation",
                    "trust_status": "Extracted",
                }
            ],
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["status"] == "created"
    assert results[1]["status"] == "rejected"
    assert results[2]["status"] == "rejected"
    assert "Home" not in results[1]["detail"]
    assert store.get("user-a", "household", HOUSEHOLD_ID) is not None
    assert store.list("user-a", "meter_checkpoints") == []


def test_file_retention_requires_consent_signature_and_ownership(cloud) -> None:
    client, store, files = cloud
    headers = _auth("token-a")
    missing_choice = client.post(
        "/api/account/files",
        headers=headers,
        data={"category": "bill", "consent": "no"},
        files={"file": ("bill.jpg", JPEG, "image/jpeg")},
    )
    assert missing_choice.status_code == 400
    assert files._files == {}

    stored = client.post(
        "/api/account/files",
        headers=headers,
        data={"category": "bill", "consent": "retain_in_account"},
        files={"file": ("bill.jpg", JPEG, "image/jpeg")},
    )
    assert stored.status_code == 200
    body = stored.json()
    assert body["retained"] is True
    assert "users/" not in stored.text
    file_id = body["id"]
    assert store.get("user-a", "retained_files", file_id)["owner_uid"] == "user-a"

    other = client.get(f"/api/account/files/{file_id}", headers=_auth("token-b"))
    assert other.status_code == 404

    download = client.get(f"/api/account/files/{file_id}", headers=headers)
    assert download.status_code == 200
    assert download.content == JPEG

    text = client.post(
        "/api/account/files",
        headers=headers,
        data={"category": "meter_photo", "consent": "retain_in_account"},
        files={"file": ("note.txt", b"not an image", "text/plain")},
    )
    assert text.status_code == 400
    assert "not an image" not in text.text

    removed = client.delete(f"/api/account/files/{file_id}", headers=headers)
    assert removed.status_code == 200
    assert files.get("user-a", file_id) is None
    assert store.get("user-a", "retained_files", file_id) is None


def test_deletion_reports_partial_failure_and_does_not_claim_completion(cloud) -> None:
    client, store, files = cloud
    headers = _auth("token-a")
    client.put(
        f"/api/account/records/household/{HOUSEHOLD_ID}",
        headers=headers,
        json=_household(),
    )
    store.fail_delete_all = True
    files.fail_deletes = True
    files.put("user-a", "file-1", JPEG, "image/jpeg")

    response = client.delete("/api/account/data?include_login=true", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["complete"] is False
    assert body["local_records_removed"] is False
    assert body["limitations"]
    assert store.get("user-a", "household", HOUSEHOLD_ID) is not None


def test_rules_deny_open_access_and_require_owner_uid() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    firestore = (root / "firebase" / "firestore.rules").read_text()
    storage = (root / "firebase" / "storage.rules").read_text()

    assert "if true" not in firestore
    assert "if true" not in storage
    assert "request.auth.uid == uid" in firestore
    assert "request.resource.data.owner_uid == request.auth.uid" in firestore
    assert "resource.data.owner_uid == request.auth.uid" in firestore
    assert "request.auth.uid == uid" in storage
    assert "image/jpeg" in storage
    assert "8 * 1024 * 1024" in storage


def test_extract_limiter_blocks_only_after_the_configured_count() -> None:
    from app.core.rate_limit import ExtractRateLimiter

    limiter = ExtractRateLimiter(2)
    assert limiter.allow("client", now=0)
    assert limiter.allow("client", now=1)
    assert limiter.allow("client", now=2) is False
    assert limiter.allow("client", now=61)
    assert ExtractRateLimiter(0).allow("client", now=0)


def test_health_stays_honest_when_firebase_credentials_exist() -> None:
    app = create_app(
        Settings(
            app_env="test",
            cors_origins=["http://localhost:3000"],
            firebase_project_id="demo-project",
            firebase_client_email="firebase-adminsdk@demo-project.iam.gserviceaccount.com",
            firebase_private_key="not-a-real-key",
        )
    )
    with TestClient(app) as client:
        response = client.get("/api/health")
    body = response.json()
    checks = {item["name"]: item for item in body["checks"]}

    assert response.status_code == 200
    assert "not connected" in body["detail"]
    assert checks["firebase"]["state"] == "not_configured"
    assert "does not call Firebase" in checks["firebase"]["detail"]
    assert "not-a-real-key" not in response.text


def test_settings_repr_hides_the_private_key() -> None:
    settings = Settings(
        app_env="test",
        cors_origins=["http://localhost:3000"],
        firebase_project_id="demo-project",
        firebase_client_email="firebase-adminsdk@demo-project.iam.gserviceaccount.com",
        firebase_private_key="super-secret-private-key",
    )

    assert settings.firebase_configured is True
    assert "super-secret-private-key" not in repr(settings)


def test_file_check_rate_limit_uses_the_existing_error_shape() -> None:
    app = create_app(
        Settings(
            app_env="test",
            cors_origins=["http://localhost:3000"],
            extract_rate_limit_per_minute=1,
        )
    )
    with TestClient(app) as client:
        first = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
        )
        second = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
        )

    assert first.status_code != 429
    assert second.status_code == 429
    assert second.json()["code"] == "unavailable"
    assert "Wait a minute" in second.json()["message"]


def test_store_error_is_safe() -> None:
    with pytest.raises(StoreError):
        raise StoreError("The record was not saved.")
