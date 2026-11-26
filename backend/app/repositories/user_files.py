"""Retained files. Object names are server-generated and scoped to the verified UID."""

from uuid import uuid4

from app.core.config import Settings
from app.repositories.user_records import StoreError


class MemoryFileStore:
    def __init__(self) -> None:
        self._files: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.fail_puts = False
        self.fail_deletes = False

    def put(self, uid: str, file_id: str, content: bytes, media_type: str) -> str:
        if self.fail_puts:
            raise StoreError("The file was not stored.")
        if not uid or not file_id or "/" in file_id:
            raise StoreError("The file was not stored.")
        self._files[(uid, file_id)] = (content, media_type)
        return file_id

    def get(self, uid: str, file_id: str) -> tuple[bytes, str] | None:
        return self._files.get((uid, file_id))

    def delete(self, uid: str, file_id: str) -> bool:
        if self.fail_deletes:
            raise StoreError("The file was not removed.")
        return self._files.pop((uid, file_id), None) is not None

    def delete_all(self, uid: str) -> int:
        keys = [key for key in self._files if key[0] == uid]
        for key in keys:
            del self._files[key]
        return len(keys)


class FirebaseFileStore:
    def __init__(self, bucket_name: str) -> None:
        self._bucket_name = bucket_name
        self._bucket = None

    def put(self, uid: str, file_id: str, content: bytes, media_type: str) -> str:
        blob = self._blob(uid, file_id)
        try:
            blob.upload_from_string(content, content_type=media_type)
        except Exception as exc:
            raise StoreError("The file was not stored.") from exc
        return file_id

    def get(self, uid: str, file_id: str) -> tuple[bytes, str] | None:
        blob = self._blob(uid, file_id)
        try:
            if not blob.exists():
                return None
            content = blob.download_as_bytes()
            media_type = blob.content_type or "application/octet-stream"
        except Exception as exc:
            raise StoreError("The file could not be read.") from exc
        return content, media_type

    def delete(self, uid: str, file_id: str) -> bool:
        blob = self._blob(uid, file_id)
        try:
            if not blob.exists():
                return False
            blob.delete()
        except Exception as exc:
            raise StoreError("The file was not removed.") from exc
        return True

    def delete_all(self, uid: str) -> int:
        removed = 0
        try:
            blobs = list(self._bucket_or_raise().list_blobs(prefix=f"users/{uid}/retained/"))
            for blob in blobs:
                blob.delete()
                removed += 1
        except Exception as exc:
            raise StoreError("Retained files were not fully removed.") from exc
        return removed

    def _blob(self, uid: str, file_id: str):
        if not uid or not file_id or "/" in file_id or ".." in file_id:
            raise StoreError("The file was not stored.")
        return self._bucket_or_raise().blob(f"users/{uid}/retained/{file_id}")

    def _bucket_or_raise(self):
        if self._bucket is not None:
            return self._bucket
        try:
            from firebase_admin import storage

            self._bucket = storage.bucket(self._bucket_name)
        except Exception as exc:
            raise StoreError("The file was not stored.") from exc
        return self._bucket


def build_file_store(settings: Settings) -> MemoryFileStore | FirebaseFileStore | None:
    if not settings.firebase_storage_configured or not settings.firebase_storage_bucket:
        return None
    return FirebaseFileStore(settings.firebase_storage_bucket)


def new_file_id() -> str:
    return str(uuid4())
