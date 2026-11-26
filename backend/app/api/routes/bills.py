"""Thin bill routes. Reading and comparison live in services."""

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.integrations.gemini.client import DocumentExtractor, GoogleGeminiExtractor
from app.integrations.gemini.errors import (
    GeminiNotConfigured,
    GeminiSchemaError,
    GeminiTimeout,
    GeminiUnavailable,
)
from app.api.limits import extraction_limited
from app.schemas.bill import BillAuditReport, BillExtractionDraft, ComplaintDraft, ConfirmedBillRequest
from app.schemas.errors import ErrorCode, ErrorResponse
from app.services.bill_audit import audit_confirmed_bill
from app.services.bill_extraction import parse_extraction
from app.services.bill_files import (
    MAX_BILL_BYTES,
    BillFileError,
    clear_upload_buffer,
    detect_bill_media,
    read_declared_type,
)
from app.services.complaint_draft import build_complaint_draft

router = APIRouter(prefix="/bills")


def _error(status: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def _extractor(request: Request) -> DocumentExtractor:
    override = getattr(request.app.state, "bill_extractor", None)
    if override is not None:
        return override
    return GoogleGeminiExtractor(request.app.state.settings)


@router.post("/extractions", response_model=BillExtractionDraft)
async def create_extraction(
    request: Request,
    file: UploadFile = File(...),
) -> BillExtractionDraft | JSONResponse:
    limited = extraction_limited(request)
    if limited is not None:
        return limited
    buffer = bytearray()
    try:
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            if len(buffer) + len(chunk) > MAX_BILL_BYTES:
                raise BillFileError("The bill file is larger than 8 MB.")
            buffer.extend(chunk)
        content = bytes(buffer)
        media_type = detect_bill_media(content, read_declared_type(file.content_type))
        payload = _extractor(request).extract_document(content, media_type)
        return parse_extraction(
            payload,
            media_type=media_type,
            model=request.app.state.settings.gemini_model,
        )
    except BillFileError as exc:
        return _error(400, ErrorCode.INVALID_REQUEST, exc.message)
    except GeminiNotConfigured:
        return _error(503, ErrorCode.UNAVAILABLE, "Bill reading is unavailable because Gemini is not configured.")
    except GeminiTimeout:
        return _error(503, ErrorCode.UNAVAILABLE, "Bill reading did not finish in time. Try the upload again.")
    except (GeminiSchemaError, GeminiUnavailable):
        return _error(503, ErrorCode.UNAVAILABLE, "The bill could not be read. No values were extracted.")
    finally:
        clear_upload_buffer(buffer)


@router.post("/audits", response_model=BillAuditReport)
def create_audit(request: Request, bill: ConfirmedBillRequest) -> BillAuditReport:
    return audit_confirmed_bill(request.app.state.tariff_catalog, bill)


@router.post("/complaint-drafts", response_model=ComplaintDraft)
def create_complaint(request: Request, bill: ConfirmedBillRequest) -> ComplaintDraft:
    report = audit_confirmed_bill(request.app.state.tariff_catalog, bill)
    return build_complaint_draft(bill, report)
