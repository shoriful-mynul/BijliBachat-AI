import json

import pytest
from fastapi.testclient import TestClient

from app.integrations.gemini.errors import GeminiNotConfigured, GeminiSchemaError, GeminiTimeout, GeminiUnavailable
from app.services.bill_files import clear_upload_buffer
from tests.bill_samples import JPEG, PDF, PNG, extraction_payload


class FakeExtractor:
    def __init__(self, payload: object | None = None, error: Exception | None = None) -> None:
        self.payload = extraction_payload() if payload is None else payload
        self.error = error
        self.calls: list[tuple[bytes, str]] = []

    def extract_document(self, content: bytes, mime_type: str) -> dict:
        self.calls.append((content, mime_type))
        if self.error:
            raise self.error
        if not isinstance(self.payload, dict):
            raise GeminiSchemaError()
        return self.payload


def _use(client: TestClient, extractor: FakeExtractor) -> FakeExtractor:
    client.app.state.bill_extractor = extractor
    return extractor


def _upload(client: TestClient, content: bytes, mime: str, name: str = "ignored.png"):
    return client.post("/api/bills/extractions", files={"file": (name, content, mime)})


def _bill(**overrides: object) -> dict:
    body = {
        "confirmation": "user_confirmed",
        "provider_code": "IESCO",
        "consumer_category": "residential",
        "tariff_type": "non_tou",
        "eligibility": "unprotected",
        "billing_date": "2026-03-01",
        "consumption_kwh": "250",
        "sanctioned_load_kw": "5",
        "energy_charge": "8275.00",
        "fixed_charge": "1750.00",
    }
    body.update(overrides)
    return body


def test_extraction_draft_is_unconfirmed_and_does_not_echo_the_file(client: TestClient) -> None:
    _use(client, FakeExtractor())
    response = _upload(client, PNG, "image/png", name="../../secret-bill.png")

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed"] is False
    assert body["provider_code"]["trust_status"] == "Extracted"
    assert body["gst"]["value"] is None
    assert "secret-bill" not in response.text
    assert PNG.hex() not in response.text


def test_pdf_upload_and_cleanup_on_success_and_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    cleared: list[int] = []

    def spy(buffer: bytearray) -> None:
        cleared.append(len(buffer))
        clear_upload_buffer(buffer)

    monkeypatch.setattr("app.api.routes.bills.clear_upload_buffer", spy)
    _use(client, FakeExtractor())
    assert _upload(client, PDF, "application/pdf", "bill.pdf").status_code == 200
    _use(client, FakeExtractor(error=GeminiUnavailable()))
    assert _upload(client, JPEG, "image/jpeg").status_code == 503
    assert cleared == [len(PDF), len(JPEG)]


def test_file_rejections(client: TestClient) -> None:
    _use(client, FakeExtractor())
    assert _upload(client, b"", "image/png").status_code == 400
    assert _upload(client, b"GIF89ahello", "image/gif").status_code == 400
    assert _upload(client, PNG, "image/jpeg").status_code == 400
    assert _upload(client, b"\xff\xd8\xff" + b"\x00" * 20, "image/jpeg").status_code == 400
    huge = b"\x00" * (8 * 1024 * 1024 + 1)
    assert _upload(client, huge, "application/octet-stream").status_code == 400


def test_gemini_failures_do_not_invent_an_extraction(client: TestClient) -> None:
    for error in (GeminiNotConfigured(), GeminiTimeout(), GeminiUnavailable(), GeminiSchemaError()):
        _use(client, FakeExtractor(error=error))
        response = _upload(client, PNG, "image/png")
        assert response.status_code == 503
        assert response.json()["code"] == "unavailable"
        assert "IESCO" not in response.text


def test_missing_server_key_is_unavailable(client: TestClient) -> None:
    response = _upload(client, PNG, "image/png")
    assert response.status_code == 503
    assert response.json()["message"].startswith("Bill reading is unavailable")


def test_audit_rejects_unconfirmed_and_uses_corrected_values(client: TestClient) -> None:
    rejected = client.post("/api/bills/audits", json={"confirmed": True, "provider_code": "IESCO"})
    assert rejected.status_code == 422

    corrected = client.post("/api/bills/audits", json=_bill(energy_charge="9000.00"))
    assert corrected.status_code == 200
    body = corrected.json()
    energy = next(item for item in body["comparisons"] if item["code"] == "energy_charge")
    total = next(item for item in body["comparisons"] if item["code"] == "total_amount_due")
    assert body["confirmed"] == "user_confirmed"
    assert energy["outcome"] == "possible_mismatch"
    assert energy["reported_amount"] == "9000.00"
    assert total["outcome"] == "not_comparable"
    assert total["calculated_amount"] is None
    assert "fraud" not in json.dumps(body).lower()


def test_confidence_cannot_confirm_an_audit(client: TestClient) -> None:
    _use(client, FakeExtractor(extraction_payload(energy_charge={"value": "1.00", "confidence": "readable", "note": None})))
    extracted = _upload(client, PNG, "image/png").json()
    assert extracted["confirmed"] is False
    response = client.post("/api/bills/audits", json={"extraction": extracted, "confidence": "readable"})
    assert response.status_code == 422


def test_complaint_draft_uses_confirmed_values_and_stays_editable(client: TestClient) -> None:
    response = client.post("/api/bills/complaint-drafts", json=_bill(energy_charge="9000.00"))
    assert response.status_code == 200
    body = response.json()
    assert body["submitted"] is False
    assert body["editable"] is True
    assert "9000.00" in body["text"]
    assert "8275.00" in body["text"]
    assert "Possible mismatch" in body["text"]
    assert "fraud" not in body["text"].lower()
    assert "unlawful" not in body["text"].lower()
    assert "[please add your name]" in body["text"]
    assert "This note has not been submitted." in body["text"]


def test_complaint_without_a_mismatch_does_not_invent_one(client: TestClient) -> None:
    response = client.post("/api/bills/complaint-drafts", json=_bill())
    assert response.status_code == 200
    text = response.json()["text"]
    assert "Possible mismatch" not in text
    assert "payable comparison may still be unavailable" in text
