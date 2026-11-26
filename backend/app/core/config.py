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

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def blank_gemini_key_is_unset(cls, value: object) -> object:
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
