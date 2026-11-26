from datetime import datetime, timezone

from app.core.config import Settings
from app.schemas.health import HealthCheck, HealthResponse


def build_health(settings: Settings) -> HealthResponse:
    """Report what is actually running. Unconnected services stay not_configured."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.version,
        environment=settings.app_env,
        detail=(
            "The API process is running. Firebase and a complete payable tariff are not connected."
            if settings.gemini_api_key
            else (
                "The API process is running. Firebase, Gemini, and a complete "
                "payable tariff are not connected."
            )
        ),
        checked_at=datetime.now(timezone.utc),
        checks=[
            HealthCheck(
                name="process",
                state="ok",
                detail="The API process handled this request.",
            ),
            HealthCheck(
                name="firebase",
                state="not_configured",
                detail=(
                    "Firebase Authentication, Firestore, and Storage are not connected."
                ),
            ),
            HealthCheck(
                name="gemini",
                state="not_configured",
                detail=(
                    "A Gemini key is configured. This check does not call Gemini."
                    if settings.gemini_api_key
                    else "Gemini is not connected."
                ),
            ),
            HealthCheck(
                name="tariff_configuration",
                state="not_configured",
                detail=(
                    "Energy and fixed-charge schedules are packaged for one company. "
                    "Taxes, duty, and fuel adjustment are not in those files, so a "
                    "payable total is not configured."
                ),
            ),
        ],
    )
