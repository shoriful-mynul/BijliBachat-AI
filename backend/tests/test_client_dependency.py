import starlette.testclient as testclient_module
from fastapi.testclient import TestClient


def test_testclient_uses_httpx2(client: TestClient) -> None:
    """Starlette 1.x prefers httpx2. Plain httpx still imports, and Starlette deprecates it here."""

    assert testclient_module.httpx.__name__ == "httpx2"

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
