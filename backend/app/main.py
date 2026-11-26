from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.schemas.errors import ErrorResponse
from app.tariffs.loader import load_production_catalog


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    catalog = load_production_catalog()
    app = FastAPI(
        title="BijliBachat AI",
        version=resolved.version,
        summary="Household electricity expense intelligence API.",
        description=(
            "The health route reports the process. Tariff routes resolve a dated "
            "configuration and calculate only the components that configuration "
            "verifies. Bill routes read a document with Gemini when a server key "
            "is configured, then compare values a person confirmed. Household and "
            "meter contracts are not exposed as routes. Field validation errors keep "
            "FastAPI's detail list. Unexpected failures use ErrorResponse and do "
            "not include the exception text."
        ),
        responses={
            500: {
                "model": ErrorResponse,
                "description": "Unexpected failure. The message does not include internal details.",
            }
        },
    )
    app.state.settings = resolved
    app.state.tariff_catalog = catalog
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
