from fastapi import APIRouter, Request

from app.core.config import Settings
from app.schemas.health import HealthResponse
from app.services.health import build_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def read_health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return build_health(settings)
