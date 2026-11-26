from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def get_version() -> str:
    try:
        return version("bijlibachat-backend")
    except PackageNotFoundError:
        return "0.1.0"


def parse_cors_origins(value: str) -> list[str]:
    """Accept a comma-separated list of explicit http(s) origins."""
    origins = [item.strip() for item in value.split(",") if item.strip()]
    validated: list[str] = []

    for origin in origins:
        if origin == "*":
            raise ValueError(
                "CORS origins must be explicit. A wildcard is not allowed."
            )

        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"Invalid CORS origin: {origin}")
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(f"Invalid CORS origin: {origin}")

        validated.append(origin.rstrip("/"))

    return validated


class Settings(BaseSettings):
    """Environment-backed process settings. Gemini is optional and stays server-side."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    service_name: str = "bijlibachat-ai-backend"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = Field(default="gemini-3.8-flash", min_length=1, max_length=80)
    gemini_timeout_seconds: int = Field(default=45, ge=5, le=120)
    firebase_project_id: str | None = None
    firebase_client_email: str | None = None
    firebase_private_key: str | None = Field(default=None, repr=False)
    firebase_storage_bucket: str | None = None
    extract_rate_limit_per_minute: int = Field(default=60, ge=0, le=600)

    @field_validator(
        "gemini_api_key",
        "firebase_project_id",
        "firebase_client_email",
        "firebase_private_key",
        "firebase_storage_bucket",
        mode="before",
    )
    @classmethod
    def blank_secret_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return parse_cors_origins(value)
        if isinstance(value, list):
            return parse_cors_origins(",".join(str(item) for item in value))
        raise ValueError("CORS origins must be a comma-separated string or a list.")

    @property
    def version(self) -> str:
        return get_version()

    @property
    def firebase_configured(self) -> bool:
        """True only when the server has Admin credentials. Tests leave these unset."""
        return bool(
            self.firebase_project_id and self.firebase_client_email and self.firebase_private_key
        )

    @property
    def firebase_storage_configured(self) -> bool:
        return self.firebase_configured and bool(self.firebase_storage_bucket)


@lru_cache
def get_settings() -> Settings:
    return Settings()
