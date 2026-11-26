"""Recognize a bill upload from its bytes. The filename is never used as a path."""

from app.integrations.gemini.errors import GeminiError

MAX_BILL_BYTES = 8 * 1024 * 1024

_JPEG = "image/jpeg"
_PNG = "image/png"
_WEBP = "image/webp"
_PDF = "application/pdf"
SUPPORTED_MEDIA_TYPES = frozenset({_JPEG, _PNG, _WEBP, _PDF})

_DECLARED_ALIASES = {
    "image/jpg": _JPEG,
    "image/jpeg": _JPEG,
    "image/png": _PNG,
    "image/webp": _WEBP,
    "application/pdf": _PDF,
}


class BillFileError(GeminiError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def clear_upload_buffer(buffer: bytearray) -> None:
    """Wipe an upload buffer, including when reading or extraction fails."""
    buffer[:] = b"\x00" * len(buffer)
    buffer.clear()


def read_declared_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    declared = content_type.split(";", 1)[0].strip().lower()
    if declared in {"", "application/octet-stream"}:
        return None
    return _DECLARED_ALIASES.get(declared, declared)


def detect_bill_media(content: bytes, declared: str | None) -> str:
    """Return the media type proved by the file signature."""
    if not content:
        raise BillFileError("The bill file is empty.")
    if len(content) > MAX_BILL_BYTES:
        raise BillFileError("The bill file is larger than 8 MB.")
    detected = _signature(content)
    if detected is None:
        raise BillFileError("The bill file is not a supported JPEG, PNG, WebP, or PDF.")
    if declared is not None and declared not in SUPPORTED_MEDIA_TYPES:
        raise BillFileError("The bill file is not a supported JPEG, PNG, WebP, or PDF.")
    if declared is not None and declared != detected:
        raise BillFileError("The file type does not match its contents.")
    return detected


def _signature(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9") and len(content) >= 16:
        return _JPEG
    if content.startswith(b"\x89PNG\r\n\x1a\n") and b"IHDR" in content[:24] and len(content) >= 24:
        return _PNG
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP" and len(content) >= 16:
        return _WEBP
    if content.startswith(b"%PDF-") and b"%%EOF" in content and len(content) >= 16:
        return _PDF
    if content.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF", b"%PDF-")):
        raise BillFileError("The bill file could not be read.")
    return None
