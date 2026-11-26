import pytest
from pydantic import ValidationError

from app.core.config import Settings, parse_cors_origins


def test_parse_cors_origins_accepts_explicit_list() -> None:
    assert parse_cors_origins(
        "http://localhost:3000, https://app.example.com"
    ) == ["http://localhost:3000", "https://app.example.com"]


def test_parse_cors_origins_rejects_wildcard() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        parse_cors_origins("*")


def test_parse_cors_origins_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="Invalid CORS origin"):
        parse_cors_origins("ftp://localhost")


def test_default_cors_allows_local_dev_hosts() -> None:
    assert Settings().cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging")


def test_settings_reject_wildcard_origin() -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(cors_origins="*")


def test_settings_do_not_require_secrets() -> None:
    settings = Settings(app_env="test")

    assert set(Settings.model_fields) == {
        "app_env",
        "service_name",
        "cors_origins",
        "gemini_api_key",
        "gemini_model",
        "gemini_timeout_seconds",
    }
    assert settings.app_env == "test"
    assert settings.gemini_api_key is None
    assert settings.gemini_model == "gemini-3.8-flash"
    assert "secret" not in settings.model_dump()
    assert "key" not in settings.model_dump()
