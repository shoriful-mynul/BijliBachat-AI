"""Account records. The UID comes from the verified token. Local mode does not pretend to save."""

import logging
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.auth.identity import (
    AuthenticatedUser,
    ExpiredIdentity,
    IdentityUnavailable,
    InvalidIdentity,
)
from app.repositories.user_files import new_file_id
from app.repositories.user_records import (
    COLLECTIONS,
    WRITABLE_COLLECTIONS,
    StoreError,
)
from app.schemas.errors import ErrorCode, ErrorResponse
from app.services.account_records import record_id_for, validate_record
from app.services.bill_files import (
    MAX_BILL_BYTES,
    BillFileError,
    clear_upload_buffer,
    detect_bill_media,
    read_declared_type,
)

router = APIRouter(prefix="/account")
logger = logging.getLogger(__name__)

_NOT_CONFIGURED = "Cloud accounts are not configured. Nothing was saved."
_SIGN_IN = "Sign in is required."
_SIGN_IN_AGAIN = "The session is no longer valid. Sign in again."
_NOT_SAVED = "The record was not saved."
_NOT_FOUND = "That record was not found."
_FILE_NOT_STORED = "The file was not stored."
_FILE_NEEDS_CHOICE = "The file was not stored. Saving a file requires an explicit choice."
_STORAGE_OFF = "File storage is not configured. The file was not kept."
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMPORT = 200


def _error(status: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def _public(record: dict) -> dict:
    return {key: value for key, value in record.items() if key != "owner_uid"}


def _identity(request: Request) -> AuthenticatedUser | JSONResponse:
    verifier = getattr(request.app.state, "token_verifier", None)
    store = getattr(request.app.state, "record_store", None)
    if verifier is None or store is None:
        return _error(503, ErrorCode.UNAVAILABLE, _NOT_CONFIGURED)
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip() or " " in token.strip():
        return _error(401, ErrorCode.INVALID_REQUEST, _SIGN_IN)
    try:
        return verifier.verify(token.strip())
    except ExpiredIdentity:
        return _error(401, ErrorCode.INVALID_REQUEST, _SIGN_IN_AGAIN)
    except InvalidIdentity:
        return _error(401, ErrorCode.INVALID_REQUEST, _SIGN_IN_AGAIN)
    except IdentityUnavailable:
        return _error(503, ErrorCode.UNAVAILABLE, "Cloud accounts are not available. Nothing was saved.")
    except Exception:
        logger.warning("account token check failed")
        return _error(401, ErrorCode.INVALID_REQUEST, _SIGN_IN_AGAIN)


@router.get("/status")
def account_status(request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    return JSONResponse(
        {
            "mode": "firebase",
            "continuous_synchronization": False,
            "signed_in": True,
        }
    )


@router.put("/records/{collection}/{record_id}")
async def put_record(collection: str, record_id: str, request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    if collection not in WRITABLE_COLLECTIONS:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    try:
        payload = await request.json()
    except Exception:
        return _error(400, ErrorCode.INVALID_REQUEST, "The record did not match the saved shape.")
    document, reason = validate_record(collection, payload)
    if document is None or reason is not None:
        return _error(400, ErrorCode.INVALID_REQUEST, reason or "The record did not match the saved shape.")
    if record_id_for(collection, _model_from(collection, document)) != record_id:
        return _error(400, ErrorCode.INVALID_REQUEST, "The record did not match the saved shape.")
    try:
        status = request.app.state.record_store.put(identity.uid, collection, record_id, document)
    except StoreError:
        return _error(503, ErrorCode.UNAVAILABLE, _NOT_SAVED)
    except Exception:
        logger.warning("account write failed: %s", "StoreFailure")
        return _error(503, ErrorCode.UNAVAILABLE, _NOT_SAVED)
    saved = request.app.state.record_store.get(identity.uid, collection, record_id)
    return JSONResponse(
        {
            "status": status,
            "id": record_id,
            "continuous_synchronization": False,
            "record": _public(saved or document),
        }
    )


@router.get("/records/{collection}/{record_id}")
def get_record(collection: str, record_id: str, request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    if collection not in COLLECTIONS:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    try:
        saved = request.app.state.record_store.get(identity.uid, collection, record_id)
    except StoreError:
        return _error(503, ErrorCode.UNAVAILABLE, "The record could not be read.")
    if saved is None:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    return JSONResponse(_public(saved))


@router.get("/records/{collection}")
def list_records(collection: str, request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    if collection not in COLLECTIONS:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    try:
        rows = request.app.state.record_store.list(identity.uid, collection)
    except StoreError:
        return _error(503, ErrorCode.UNAVAILABLE, "The records could not be read.")
    return JSONResponse({"records": [_public(row) for row in rows], "continuous_synchronization": False})


@router.delete("/records/{collection}/{record_id}")
def delete_record(collection: str, record_id: str, request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    if collection == "retained_files":
        return _delete_retained_record(request, identity.uid, record_id)
    if collection not in WRITABLE_COLLECTIONS:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    try:
        removed = request.app.state.record_store.delete(identity.uid, collection, record_id)
    except StoreError:
        return _error(503, ErrorCode.UNAVAILABLE, "The record was not removed.")
    if not removed:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    return JSONResponse({"removed": True, "file": "none"})


@router.post("/import")
async def import_records(request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    try:
        payload = await request.json()
    except Exception:
        return _error(400, ErrorCode.INVALID_REQUEST, "The copy did not match the saved shape.")
    if not isinstance(payload, dict):
        return _error(400, ErrorCode.INVALID_REQUEST, "The copy did not match the saved shape.")
    unknown = [key for key in payload if key not in WRITABLE_COLLECTIONS]
    if unknown:
        return _error(400, ErrorCode.INVALID_REQUEST, "The copy did not match the saved shape.")
    results: list[dict[str, Any]] = []
    for collection in WRITABLE_COLLECTIONS:
        items = payload.get(collection, [])
        if not isinstance(items, list):
            return _error(400, ErrorCode.INVALID_REQUEST, "The copy did not match the saved shape.")
        if len(items) > _MAX_IMPORT:
            return _error(400, ErrorCode.INVALID_REQUEST, "The copy is too large. Nothing new was saved.")
        for item in items:
            results.append(_import_one(request, identity.uid, collection, item))
    return JSONResponse(
        {
            "results": results,
            "local_records_removed": False,
            "continuous_synchronization": False,
        }
    )


@router.get("/export")
def export_records(request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    exported: dict[str, list[dict]] = {}
    try:
        for collection in COLLECTIONS:
            exported[collection] = [
                _public(row) for row in request.app.state.record_store.list(identity.uid, collection)
            ]
    except StoreError:
        return _error(503, ErrorCode.UNAVAILABLE, "The download did not finish.")
    return JSONResponse({"records": exported, "continuous_synchronization": False})


@router.delete("/data")
def delete_account_data(request: Request, include_login: bool = False) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    limitations: list[str] = []
    files_removed = 0
    files_cleared = True
    documents_removed = 0
    documents_cleared = True
    file_store = getattr(request.app.state, "file_store", None)
    if file_store is not None:
        try:
            files_removed = file_store.delete_all(identity.uid)
        except StoreError:
            files_cleared = False
            limitations.append("Retained files were not fully removed.")
    else:
        limitations.append("File storage is not configured, so no stored file was removed.")
    try:
        documents_removed = request.app.state.record_store.delete_all(identity.uid)
    except StoreError:
        documents_cleared = False
        limitations.append("Account records were not fully removed.")
    login_deleted = False
    if include_login:
        try:
            login_deleted = bool(request.app.state.token_verifier.delete_login(identity.uid))
        except Exception:
            login_deleted = False
        if not login_deleted:
            limitations.append("The sign-in was not deleted.")
    else:
        limitations.append("The sign-in was kept.")
    complete = documents_cleared and files_cleared and (login_deleted or not include_login)
    return JSONResponse(
        {
            "documents_removed": documents_removed,
            "files_removed": files_removed,
            "documents_cleared": documents_cleared,
            "files_cleared": files_cleared,
            "login_deleted": login_deleted,
            "complete": complete,
            "local_records_removed": False,
            "limitations": limitations,
        }
    )


@router.post("/files")
async def retain_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form(...),
    consent: str = Form(...),
) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    if consent != "retain_in_account":
        return _error(400, ErrorCode.INVALID_REQUEST, _FILE_NEEDS_CHOICE)
    if category not in {"bill", "meter_photo"}:
        return _error(400, ErrorCode.INVALID_REQUEST, _FILE_NOT_STORED)
    file_store = getattr(request.app.state, "file_store", None)
    if file_store is None:
        return _error(503, ErrorCode.UNAVAILABLE, _STORAGE_OFF)
    buffer = bytearray()
    try:
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            if len(buffer) + len(chunk) > MAX_BILL_BYTES:
                return _error(400, ErrorCode.INVALID_REQUEST, "The file is larger than 8 MB. It was not stored.")
            buffer.extend(chunk)
        content = bytes(buffer)
        media_type = detect_bill_media(content, read_declared_type(file.content_type))
        if category == "meter_photo" and media_type not in _IMAGE_TYPES:
            return _error(400, ErrorCode.INVALID_REQUEST, "A meter photo must be a JPEG, PNG, or WebP. It was not stored.")
    except BillFileError:
        return _error(400, ErrorCode.INVALID_REQUEST, "The file type is not supported. It was not stored.")
    finally:
        clear_upload_buffer(buffer)
    file_id = new_file_id()
    metadata = {
        "id": file_id,
        "category": category,
        "media_type": media_type,
        "byte_size": len(content),
        "consent": "retain_in_account",
    }
    uploaded = False
    try:
        file_store.put(identity.uid, file_id, content, media_type)
        uploaded = True
        request.app.state.record_store.put(identity.uid, "retained_files", file_id, metadata)
    except StoreError:
        if uploaded:
            _discard_uploaded_file(file_store, identity.uid, file_id)
        return _error(503, ErrorCode.UNAVAILABLE, _FILE_NOT_STORED)
    except Exception:
        if uploaded:
            _discard_uploaded_file(file_store, identity.uid, file_id)
        logger.warning("account file write failed")
        return _error(503, ErrorCode.UNAVAILABLE, _FILE_NOT_STORED)
    return JSONResponse(
        {
            "id": file_id,
            "media_type": media_type,
            "byte_size": len(content),
            "retained": True,
            "continuous_synchronization": False,
        }
    )


@router.get("/files/{file_id}")
def download_file(file_id: str, request: Request) -> Response:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    file_store = getattr(request.app.state, "file_store", None)
    if file_store is None:
        return _error(503, ErrorCode.UNAVAILABLE, _STORAGE_OFF)
    try:
        meta = request.app.state.record_store.get(identity.uid, "retained_files", file_id)
        stored = file_store.get(identity.uid, file_id)
    except StoreError:
        return _error(503, ErrorCode.UNAVAILABLE, "The file could not be read.")
    if meta is None or stored is None or meta.get("owner_uid") != identity.uid:
        return _error(404, ErrorCode.NOT_FOUND, "That file was not found.")
    content, media_type = stored
    return Response(content=content, media_type=str(meta.get("media_type") or media_type))


@router.delete("/files/{file_id}")
def delete_file(file_id: str, request: Request) -> JSONResponse:
    identity = _identity(request)
    if isinstance(identity, JSONResponse):
        return identity
    removed = _delete_owned_file(request, identity.uid, file_id)
    if removed is None:
        return _error(503, ErrorCode.UNAVAILABLE, "The file was not removed.")
    if not removed:
        return _error(404, ErrorCode.NOT_FOUND, "That file was not found.")
    return JSONResponse({"removed": True})


def _import_one(request: Request, uid: str, collection: str, item: object) -> dict[str, Any]:
    document, reason = validate_record(collection, item)
    if document is None:
        return {"collection": collection, "id": _loose_id(item), "status": "rejected", "detail": reason}
    from app.services.account_records import _MODELS

    model = _MODELS[collection].model_validate(document)
    record_id = record_id_for(collection, model)
    try:
        status = request.app.state.record_store.put(uid, collection, record_id, document)
    except StoreError:
        return {
            "collection": collection,
            "id": record_id,
            "status": "rejected",
            "detail": "The record was not saved.",
        }
    return {"collection": collection, "id": record_id, "status": status, "detail": None}


def _loose_id(item: object) -> str | None:
    if isinstance(item, dict):
        value = item.get("id", item.get("cycle_id"))
        if isinstance(value, str):
            return value
    return None


def _model_from(collection: str, document: dict):
    from app.services.account_records import _MODELS

    return _MODELS[collection].model_validate(document)


def _discard_uploaded_file(file_store, uid: str, file_id: str) -> None:
    try:
        file_store.delete(uid, file_id)
    except Exception:
        logger.warning("account file cleanup failed")


def _delete_retained_record(request: Request, uid: str, record_id: str) -> JSONResponse:
    removed = _delete_owned_file(request, uid, record_id)
    if removed is None:
        return _error(503, ErrorCode.UNAVAILABLE, "The record was not removed.")
    if not removed:
        return _error(404, ErrorCode.NOT_FOUND, _NOT_FOUND)
    return JSONResponse({"removed": True, "file": "removed"})


def _delete_owned_file(request: Request, uid: str, file_id: str) -> bool | None:
    file_store = getattr(request.app.state, "file_store", None)
    if file_store is None:
        return False
    try:
        object_removed = file_store.delete(uid, file_id)
        record_removed = request.app.state.record_store.delete(uid, "retained_files", file_id)
    except StoreError:
        return None
    return object_removed or record_removed
