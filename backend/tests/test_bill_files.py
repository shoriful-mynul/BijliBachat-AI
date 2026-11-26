from pathlib import Path

from app.services.bill_files import MAX_BILL_BYTES, BillFileError, clear_upload_buffer, detect_bill_media
from tests.bill_samples import JPEG, PDF, PNG, WEBP

import pytest


def test_supported_image_and_pdf_signatures() -> None:
    assert detect_bill_media(PNG, "image/png") == "image/png"
    assert detect_bill_media(JPEG, "image/jpeg") == "image/jpeg"
    assert detect_bill_media(WEBP, None) == "image/webp"
    assert detect_bill_media(PDF, "application/pdf") == "application/pdf"


def test_unsupported_extension_and_mime_are_rejected() -> None:
    with pytest.raises(BillFileError):
        detect_bill_media(b"GIF89a" + b"\x00" * 16, "image/gif")
    with pytest.raises(BillFileError, match="does not match"):
        detect_bill_media(PNG, "image/jpeg")


def test_invalid_signature_empty_and_corrupt_files_are_rejected() -> None:
    with pytest.raises(BillFileError, match="empty"):
        detect_bill_media(b"", None)
    with pytest.raises(BillFileError, match="not a supported"):
        detect_bill_media(b"not-a-bill-document", None)
    with pytest.raises(BillFileError, match="could not be read"):
        detect_bill_media(b"\xff\xd8\xff" + b"\x00" * 20, None)
    with pytest.raises(BillFileError, match="could not be read"):
        detect_bill_media(b"%PDF-1.4\ntruncated", None)


def test_oversized_upload_is_rejected_before_it_is_treated_as_a_bill() -> None:
    with pytest.raises(BillFileError, match="8 MB"):
        detect_bill_media(b"\x00" * (MAX_BILL_BYTES + 1), None)


def test_upload_buffer_is_cleared() -> None:
    buffer = bytearray(b"account-99123-secret")
    clear_upload_buffer(buffer)
    assert buffer == bytearray()


def test_validation_does_not_create_an_upload_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    detect_bill_media(PNG, None)
    assert list(tmp_path.iterdir()) == []
