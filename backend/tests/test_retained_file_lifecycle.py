"""Retained-file upload cleanup and single deletion. No production Firebase credentials."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.auth.identity import AuthenticatedUser
from app.auth.verifier import FakeTokenVerifier
from app.core.config import Settings
from app.main import create_app
from app.repositories.user_files import MemoryFileStore
from app.repositories.user_records import MemoryRecordStore, StoreError

JPEG = b"\xff\xd8\xff" + b"\x00" * 16 + b"\xff\xd9"
HOUSEHOLD_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class CountingFiles(MemoryFileStore):
    def __init__(self) -> None:
        super().__init__()
        self.deletes = 0

    def delete(self, uid: str, file_id: str) -> bool:
        self.deletes += 1
        return super().delete(uid, file_id)


class CountingRecords(MemoryRecordStore):
    def __init__(self) -> None:
        super().__init__()
        self.deletes = 0
        self.puts = 0
        self.fail_retained_with: Exception | None = None

    def put(self, uid: str, collection: str, record_id: str, payload: dict) -> str:
        self.puts += 1
        if collection == "retained_files" and self.fail_retained_with is not None:
            raise self.fail_retained_with
        return super().put(uid, collection, record_id, payload)

    def delete(self, uid: str, collection: str, record_id: str) -> bool:
        self.deletes += 1
        return super().delete(uid, collection, record_id)


class CleanupFails(CountingFiles):
    def delete(self, uid: str, file_id: str) -> bool:
        self.deletes += 1
        raise RuntimeError("private_key=secret-value bytes=ffd8")


def _app(files: MemoryFileStore, store: MemoryRecordStore):
    app = create_app(Settings(app_env="test", cors_origins=["http://localhost:3000"]))
    app.state.token_verifier = FakeTokenVerifier(
        {
            "token-a": AuthenticatedUser(uid="user-a", email="a@example.com"),
            "token-b": AuthenticatedUser(uid="user-b", email="b@example.com"),
        }
    )
    app.state.record_store = store
    app.state.file_store = files
    return app


def _auth(token: str = "token-a") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient, token: str = "token-a"):
    return client.post(
        "/api/account/files",
        headers=_auth(token),
        data={"category": "bill", "consent": "retain_in_account"},
        files={"file": ("bill.jpg", JPEG, "image/jpeg")},
    )


def test_upload_persists_the_object_and_metadata() -> None:
    files = CountingFiles()
    store = CountingRecords()
    with TestClient(_app(files, store)) as client:
        missing = client.post(
            "/api/account/files",
            headers=_auth(),
            data={"category": "bill", "consent": "no"},
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
        )
        stored = _upload(client)

    assert missing.status_code == 400
    assert stored.status_code == 200
    body = stored.json()
    assert body["retained"] is True
    assert files.get("user-a", body["id"]) == (JPEG, "image/jpeg")
    assert store.get("user-a", "retained_files", body["id"])["owner_uid"] == "user-a"
    assert "users/" not in stored.text


def test_storage_upload_failure_writes_no_metadata() -> None:
    files = CountingFiles()
    files.fail_puts = True
    store = CountingRecords()
    with TestClient(_app(files, store)) as client:
        response = _upload(client)

    assert response.status_code == 503
    assert response.json()["message"] == "The file was not stored."
    assert files._files == {}
    assert store.puts == 0
    assert store.list("user-a", "retained_files") == []


@pytest.mark.parametrize(
    "failure",
    [StoreError("The record was not saved."), RuntimeError("private_key=secret-value")],
)
def test_metadata_failure_removes_the_uploaded_object(failure: Exception, caplog: pytest.LogCaptureFixture) -> None:
    files = CountingFiles()
    store = CountingRecords()
    store.fail_retained_with = failure
    with caplog.at_level(logging.WARNING, logger="app.api.routes.account"):
        with TestClient(_app(files, store)) as client:
            response = _upload(client)

    assert response.status_code == 503
    assert response.json()["code"] == "unavailable"
    assert response.json()["message"] == "The file was not stored."
    assert "secret-value" not in response.text
    assert "secret-value" not in caplog.text
    assert files._files == {}
    assert files.deletes == 1
    assert store.list("user-a", "retained_files") == []
    assert "account file cleanup failed" not in caplog.text


def test_cleanup_failure_keeps_the_original_error(caplog: pytest.LogCaptureFixture) -> None:
    files = CleanupFails()
    store = CountingRecords()
    store.fail_retained_with = StoreError("The record was not saved.")
    with caplog.at_level(logging.WARNING, logger="app.api.routes.account"):
        with TestClient(_app(files, store)) as client:
            response = _upload(client)

    assert response.status_code == 503
    assert response.json()["message"] == "The file was not stored."
    assert "secret-value" not in response.text
    assert "private_key" not in caplog.text
    assert "ffd8" not in caplog.text
    assert "account file cleanup failed" in caplog.text
    assert files._files != {}


def test_file_route_deletes_once_and_a_missing_file_is_not_found() -> None:
    files = CountingFiles()
    store = CountingRecords()
    with TestClient(_app(files, store)) as client:
        stored = _upload(client)
        file_id = stored.json()["id"]
        removed = client.delete(f"/api/account/files/{file_id}", headers=_auth())
        after_success = (files.deletes, store.deletes)
        missing = client.delete(f"/api/account/files/{file_id}", headers=_auth())
        other_missing = client.delete("/api/account/files/missing-file", headers=_auth())

    assert removed.status_code == 200
    assert removed.json() == {"removed": True}
    assert after_success == (1, 1)
    assert files.get("user-a", file_id) is None
    assert store.get("user-a", "retained_files", file_id) is None
    assert missing.status_code == 404
    assert missing.json()["message"] == "That file was not found."
    assert other_missing.status_code == 404


def test_records_route_deletes_a_retained_file_once() -> None:
    files = CountingFiles()
    store = CountingRecords()
    with TestClient(_app(files, store)) as client:
        stored = _upload(client)
        file_id = stored.json()["id"]
        removed = client.delete(f"/api/account/records/retained_files/{file_id}", headers=_auth())
        after_success = (files.deletes, store.deletes)
        again = client.delete(f"/api/account/records/retained_files/{file_id}", headers=_auth())

    assert removed.status_code == 200
    assert removed.json() == {"removed": True, "file": "removed"}
    assert after_success == (1, 1)
    assert again.status_code == 404
    assert again.json()["message"] == "That record was not found."
    assert files.get("user-a", file_id) is None
    assert store.get("user-a", "retained_files", file_id) is None


def test_metadata_only_delete_is_successful() -> None:
    files = CountingFiles()
    store = CountingRecords()
    store.put(
        "user-a",
        "retained_files",
        "meta-only",
        {"id": "meta-only", "category": "bill", "media_type": "image/jpeg", "byte_size": 1, "consent": "retain_in_account"},
    )
    with TestClient(_app(files, store)) as client:
        response = client.delete("/api/account/files/meta-only", headers=_auth())

    assert response.status_code == 200
    assert response.json() == {"removed": True}
    assert store.get("user-a", "retained_files", "meta-only") is None


def test_cross_user_cannot_delete_a_retained_file() -> None:
    files = CountingFiles()
    store = CountingRecords()
    with TestClient(_app(files, store)) as client:
        stored = _upload(client)
        file_id = stored.json()["id"]
        by_file = client.delete(f"/api/account/files/{file_id}", headers=_auth("token-b"))
        by_record = client.delete(
            f"/api/account/records/retained_files/{file_id}",
            headers=_auth("token-b"),
        )
        download = client.get(f"/api/account/files/{file_id}", headers=_auth())

    assert by_file.status_code == 404
    assert by_record.status_code == 404
    assert download.status_code == 200
    assert download.content == JPEG
    assert store.get("user-a", "retained_files", file_id)["owner_uid"] == "user-a"


def test_other_record_deletion_does_not_remove_a_retained_file() -> None:
    files = CountingFiles()
    store = CountingRecords()
    household = {
        "id": HOUSEHOLD_ID,
        "display_name": "Home",
        "provider_code": "IESCO",
        "service_region": "Islamabad",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }
    with TestClient(_app(files, store)) as client:
        stored = _upload(client)
        file_id = stored.json()["id"]
        client.put(f"/api/account/records/household/{HOUSEHOLD_ID}", headers=_auth(), json=household)
        removed = client.delete(f"/api/account/records/household/{HOUSEHOLD_ID}", headers=_auth())

    assert removed.status_code == 200
    assert removed.json()["file"] == "none"
    assert files.get("user-a", file_id) is not None
    assert store.get("user-a", "retained_files", file_id) is not None
