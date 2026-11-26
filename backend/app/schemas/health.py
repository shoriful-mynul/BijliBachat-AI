from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    name: Literal["process", "firebase", "gemini", "tariff_configuration"]
    state: Literal["ok", "not_configured"]
    detail: str = Field(min_length=1)


class HealthResponse(BaseModel):
    """Process health. `status` does not claim that tariff or AI services are ready."""

    status: Literal["ok"]
    service: str
    version: str
    environment: Literal["development", "test", "production"]
    detail: str
    checked_at: datetime
    checks: list[HealthCheck]
