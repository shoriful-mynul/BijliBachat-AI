"""User-owned records. Callers pass the UID from a verified token, never from the body."""

from typing import Protocol

from app.core.config import Settings

COLLECTIONS = (
    "household",
    "meter_checkpoints",
    "bill_audits",
    "appliances",
    "forecast_snapshots",
    "history_cycles",
    "history_baselines",
    "retained_files",
)

WRITABLE_COLLECTIONS = tuple(name for name in COLLECTIONS if name != "retained_files")


class StoreError(Exception):
    """A remote write did not finish. The message is safe to show."""


class UserRecordStore(Protocol):
    def put(self, uid: str, collection: str, record_id: str, payload: dict) -> str:
        """Create a record. Return created or already_present. Do not replace an existing id."""

    def get(self, uid: str, collection: str, record_id: str) -> dict | None:
        """Return the record owned by uid, or None."""

    def list(self, uid: str, collection: str) -> list[dict]:
        """Return records owned by uid."""

    def delete(self, uid: str, collection: str, record_id: str) -> bool:
        """Delete one owned record. False means it was not removed."""

    def delete_all(self, uid: str) -> int:
        """Delete every record owned by uid. Raise StoreError if the clear did not finish."""


class MemoryRecordStore:
    """Process-local store used by tests and by the app only when a test injects it."""

    def __init__(self) -> None:
        self._docs: dict[tuple[str, str, str], dict] = {}
        self.fail_puts = False
        self.fail_delete_all = False

    def put(self, uid: str, collection: str, record_id: str, payload: dict) -> str:
        if self.fail_puts:
            raise StoreError("The record was not saved.")
        if collection not in COLLECTIONS:
            raise StoreError("The record was not saved.")
        key = (uid, collection, record_id)
        if key in self._docs:
            return "already_present"
        stored = {key_name: value for key_name, value in payload.items() if key_name != "owner_uid"}
        stored["owner_uid"] = uid
        self._docs[key] = stored
        return "created"

    def get(self, uid: str, collection: str, record_id: str) -> dict | None:
        stored = self._docs.get((uid, collection, record_id))
        if stored is None or stored.get("owner_uid") != uid:
            return None
        return dict(stored)

    def list(self, uid: str, collection: str) -> list[dict]:
        rows = [
            dict(stored)
            for (owner, name, _), stored in self._docs.items()
            if owner == uid and name == collection and stored.get("owner_uid") == uid
        ]
        return rows

    def delete(self, uid: str, collection: str, record_id: str) -> bool:
        key = (uid, collection, record_id)
        stored = self._docs.get(key)
        if stored is None or stored.get("owner_uid") != uid:
            return False
        del self._docs[key]
        return True

    def delete_all(self, uid: str) -> int:
        if self.fail_delete_all:
            raise StoreError("Account records were not fully removed.")
        keys = [key for key in self._docs if key[0] == uid]
        for key in keys:
            del self._docs[key]
        return len(keys)


class FirestoreRecordStore:
    """Admin SDK writes. Security rules are a second layer for the client SDK."""

    def __init__(self) -> None:
        self._client = None

    def put(self, uid: str, collection: str, record_id: str, payload: dict) -> str:
        if collection not in COLLECTIONS or not _safe_id(record_id):
            raise StoreError("The record was not saved.")
        stored = {key: value for key, value in payload.items() if key != "owner_uid"}
        stored["owner_uid"] = uid
        document = self._document(uid, collection, record_id)
        try:
            existing = document.get()
            if existing.exists:
                current = existing.to_dict() or {}
                if current.get("owner_uid") != uid:
                    raise StoreError("The record was not saved.")
                return "already_present"
            document.create(stored)
        except StoreError:
            raise
        except Exception as exc:
            if getattr(exc, "code", None) == 6 or exc.__class__.__name__ == "AlreadyExists":
                return "already_present"
            raise StoreError("The record was not saved.") from exc
        return "created"

    def get(self, uid: str, collection: str, record_id: str) -> dict | None:
        if not _safe_id(record_id):
            return None
        try:
            snapshot = self._document(uid, collection, record_id).get()
        except Exception as exc:
            raise StoreError("The record could not be read.") from exc
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        if data.get("owner_uid") != uid:
            return None
        return data

    def list(self, uid: str, collection: str) -> list[dict]:
        if collection not in COLLECTIONS:
            return []
        try:
            snapshots = self._client_or_raise().collection(f"users/{uid}/{collection}").stream()
        except Exception as exc:
            raise StoreError("The records could not be read.") from exc
        return [
            data
            for snapshot in snapshots
            if (data := snapshot.to_dict() or {}).get("owner_uid") == uid
        ]

    def delete(self, uid: str, collection: str, record_id: str) -> bool:
        current = self.get(uid, collection, record_id)
        if current is None:
            return False
        try:
            self._document(uid, collection, record_id).delete()
        except Exception as exc:
            raise StoreError("The record was not removed.") from exc
        return True

    def delete_all(self, uid: str) -> int:
        removed = 0
        try:
            client = self._client_or_raise()
            for collection in COLLECTIONS:
                for snapshot in client.collection(f"users/{uid}/{collection}").stream():
                    data = snapshot.to_dict() or {}
                    if data.get("owner_uid") != uid:
                        continue
                    snapshot.reference.delete()
                    removed += 1
        except Exception as exc:
            raise StoreError("Account records were not fully removed.") from exc
        return removed

    def _document(self, uid: str, collection: str, record_id: str):
        return self._client_or_raise().document(f"users/{uid}/{collection}/{record_id}")

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        try:
            from firebase_admin import firestore

            self._client = firestore.client()
        except Exception as exc:
            raise StoreError("The record was not saved.") from exc
        return self._client


def build_record_store(settings: Settings) -> UserRecordStore | None:
    if not settings.firebase_configured:
        return None
    return FirestoreRecordStore()


def _safe_id(value: str) -> bool:
    return bool(value) and "/" not in value and ".." not in value and len(value) <= 80
