import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.household import HouseholdProfile


def test_error_response_accepts_known_codes_only() -> None:
    body = ErrorResponse(code=ErrorCode.NOT_FOUND, message="That record is not available.")

    assert body.model_dump(mode="json") == {
        "code": "not_found",
        "message": "That record is not available.",
    }

    with pytest.raises(ValidationError):
        ErrorResponse.model_validate({"code": "fraud", "message": "no"})
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate({"code": "not_found", "message": "ok", "traceback": "secret"})
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate({"code": "not_found", "message": ""})


def test_openapi_documents_health_and_the_error_contract(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert "/api/health" in body["paths"]
    schemas = body["components"]["schemas"]
    assert "HealthResponse" in schemas
    assert "ErrorResponse" in schemas
    assert "HouseholdProfile" not in schemas
    assert "MeterReading" not in schemas


def test_unknown_route_keeps_the_http_error_shape(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_field_validation_keeps_the_fastapi_detail_list() -> None:
    app = create_app(Settings(app_env="test", cors_origins=["http://localhost:3000"]))

    @app.post("/api/_contract/household")
    def preview(body: HouseholdProfile) -> HouseholdProfile:
        return body

    with TestClient(app) as test_client:
        response = test_client.post("/api/_contract/household", json={"display_name": "A"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert "loc" in detail[0]
    assert "msg" in detail[0]


def test_unexpected_failure_hides_the_exception_text(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(Settings(app_env="production", cors_origins=["https://app.example.com"]))

    @app.get("/api/_contract/fail")
    def fail() -> None:
        raise RuntimeError("household=Ayesha token=secret-value")

    with caplog.at_level(logging.ERROR, logger="bijlibachat.api"):
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/_contract/fail")

    assert response.status_code == 500
    body = ErrorResponse.model_validate(response.json())
    assert body.code is ErrorCode.INTERNAL_ERROR
    assert body.message == "The request could not be completed."
    serialized = response.text
    assert "Ayesha" not in serialized
    assert "secret-value" not in serialized
    assert "RuntimeError" not in serialized
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in logged
    assert "Ayesha" not in logged
    assert "secret-value" not in logged
