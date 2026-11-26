"""Thin meter routes. Validation and Cliff Guard maths live in services."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.integrations.gemini.client import GoogleGeminiExtractor
from app.integrations.gemini.errors import (
    GeminiNotConfigured,
    GeminiSchemaError,
    GeminiTimeout,
    GeminiUnavailable,
)
from app.repositories.meter_ledger import NotRetainedLedger
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.meter_api import (
    AcceptedCheckpoint,
    CliffGuardRequest,
    CliffGuardResponse,
    MeterExtractionDraft,
    MeterLedgerNotice,
    MeterValidationResponse,
    SubmitMeterReadingRequest,
)
from app.schemas.meter_reading import MeterReading
from app.services.bill_files import MAX_BILL_BYTES, BillFileError, clear_upload_buffer, detect_bill_media, read_declared_type
from app.services.cliff_guard import empty_cliff_request, evaluate_cliff_guard
from app.services.meter_extraction import parse_meter_extraction
from app.services.meter_validation import validate_reading

router = APIRouter()

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_LEDGER_LIMITATION = (
    "This API does not keep meter readings. Confirmed checkpoints can stay in this browser. "
    "They remain after a refresh of this browser and are lost on another device. "
    "Restarting the API does not restore them, because they were never stored on the server. "
    "Meter photos are not stored."
)


def _error(status: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def _ledger(request: Request) -> NotRetainedLedger:
    ledger = getattr(request.app.state, "meter_ledger", None)
    if ledger is None:
        ledger = NotRetainedLedger()
        request.app.state.meter_ledger = ledger
    return ledger


def _meter_extractor(request: Request):
    override = getattr(request.app.state, "meter_extractor", None)
    if override is not None:
        return override
    return GoogleGeminiExtractor(request.app.state.settings)


@router.post("/meter-readings/extractions", response_model=MeterExtractionDraft)
async def extract_meter_photo(
    request: Request,
    file: UploadFile = File(...),
) -> MeterExtractionDraft | JSONResponse:
    buffer = bytearray()
    try:
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            if len(buffer) + len(chunk) > MAX_BILL_BYTES:
                raise BillFileError("The meter photo is larger than 8 MB.")
            buffer.extend(chunk)
        content = bytes(buffer)
        media_type = detect_bill_media(content, read_declared_type(file.content_type))
        if media_type not in _IMAGE_TYPES:
            raise BillFileError("A meter photo must be a JPEG, PNG, or WebP image.")
        payload = _meter_extractor(request).extract_meter_photo(content, media_type)
        return parse_meter_extraction(
            payload,
            media_type=media_type,
            model=request.app.state.settings.gemini_model,
        )
    except BillFileError as exc:
        return _error(400, ErrorCode.INVALID_REQUEST, exc.message)
    except GeminiNotConfigured:
        return _error(503, ErrorCode.UNAVAILABLE, "Meter reading is unavailable because Gemini is not configured.")
    except GeminiTimeout:
        return _error(503, ErrorCode.UNAVAILABLE, "Meter reading did not finish in time. Try the photo again.")
    except (GeminiSchemaError, GeminiUnavailable):
        return _error(503, ErrorCode.UNAVAILABLE, "The meter photo could not be read. No reading was extracted.")
    finally:
        clear_upload_buffer(buffer)


@router.get("/meter-readings", response_model=MeterLedgerNotice)
def list_meter_readings(request: Request, household_id: UUID | None = None) -> MeterLedgerNotice:
    retained = _ledger(request).list_for(household_id) if household_id is not None else []
    return MeterLedgerNotice(
        readings=[_public_checkpoint(item) for item in retained],
        limitation=_LEDGER_LIMITATION,
    )


@router.post("/meter-readings", response_model=MeterValidationResponse)
def submit_meter_reading(request: Request, body: SubmitMeterReadingRequest) -> MeterValidationResponse:
    result = validate_reading(
        household_id=body.household_id,
        reading=body.reading,
        prior_readings=body.prior_readings,
    )
    if result.accepted and result.checkpoint is not None:
        _ledger(request).add(_accepted_to_domain(body, result))
    return result


@router.get("/cliff-guard", response_model=CliffGuardResponse)
def read_cliff_guard(request: Request) -> CliffGuardResponse:
    return evaluate_cliff_guard(request.app.state.tariff_catalog, empty_cliff_request(datetime.now(UTC)))


@router.post("/cliff-guard", response_model=CliffGuardResponse)
def calculate_cliff_guard(request: Request, body: CliffGuardRequest) -> CliffGuardResponse:
    return evaluate_cliff_guard(request.app.state.tariff_catalog, body)


def _accepted_to_domain(body: SubmitMeterReadingRequest, result: MeterValidationResponse) -> MeterReading:
    checkpoint = result.checkpoint
    if checkpoint is None:
        raise RuntimeError("An accepted checkpoint is missing.")
    return MeterReading(
        id=checkpoint.id,
        household_id=body.household_id,
        register_kwh=body.reading.register_kwh,
        read_at=checkpoint.read_at,
        capture_method=checkpoint.capture_method,
        confirmation_state="confirmed",
        trust_status=checkpoint.trust_status,
    )


def _public_checkpoint(item: MeterReading) -> AcceptedCheckpoint:
    return AcceptedCheckpoint(
        id=item.id,
        household_id=item.household_id,
        register_kwh=f"{item.register_kwh:.3f}",
        read_at=item.read_at,
        capture_method=item.capture_method,
        confirmation_state="confirmed",
        trust_status=item.trust_status,
        warnings=[],
    )
