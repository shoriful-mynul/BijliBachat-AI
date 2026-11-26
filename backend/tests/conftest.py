import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        Settings(
            app_env="test",
            cors_origins=["http://localhost:3000"],
            firebase_project_id=None,
            firebase_client_email=None,
            firebase_private_key=None,
            firebase_storage_bucket=None,
        )
    )
    with TestClient(app) as test_client:
        yield test_client
