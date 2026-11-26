from datetime import datetime

from fastapi.testclient import TestClient


def test_health_reports_process_without_claiming_integrations(
    client: TestClient,
) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "bijlibachat-ai-backend"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
    assert "not connected" in body["detail"]
    datetime.fromisoformat(body["checked_at"].replace("Z", "+00:00"))

    checks = {item["name"]: item for item in body["checks"]}
    assert checks["process"]["state"] == "ok"
    assert checks["firebase"]["state"] == "not_configured"
    assert checks["gemini"]["state"] == "not_configured"
    assert checks["tariff_configuration"]["state"] == "not_configured"

    serialized = response.text.lower()
    assert "fraud" not in serialized
    assert "protected" not in serialized
    assert "200 unit" not in serialized
    assert "200-unit" not in serialized


def test_health_allows_configured_browser_origin(client: TestClient) -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_does_not_reflect_unknown_origin(client: TestClient) -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": "https://unknown.example"},
    )

    assert response.headers.get("access-control-allow-origin") is None
