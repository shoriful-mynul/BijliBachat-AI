"""Tariff inspection and calculation routes. Formulas stay in the engine."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.schemas.tariff import (
    TariffCalculationRequest,
    TariffCalculationResponse,
    TariffCatalogResponse,
    TariffResolutionQuery,
    TariffResolutionResponse,
)
from app.services.tariff_engine import calculate_tariff, list_configurations, resolve_tariff
from app.tariffs.loader import TariffCatalog

router = APIRouter(prefix="/tariffs")


def _catalog(request: Request) -> TariffCatalog:
    return request.app.state.tariff_catalog


@router.get("", response_model=TariffCatalogResponse)
def read_tariffs(request: Request) -> TariffCatalogResponse:
    return list_configurations(_catalog(request))


@router.get("/resolve", response_model=TariffResolutionResponse)
def read_tariff_resolution(
    request: Request,
    provider_code: Annotated[str, Query()],
    consumer_category: Annotated[str, Query()],
    tariff_type: Annotated[str, Query()],
    billing_date: Annotated[str, Query()],
    eligibility: Annotated[str | None, Query()] = None,
) -> TariffResolutionResponse:
    try:
        query = TariffResolutionQuery.model_validate(
            {
                "provider_code": provider_code,
                "consumer_category": consumer_category,
                "tariff_type": tariff_type,
                "eligibility": eligibility,
                "billing_date": billing_date,
            }
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    return resolve_tariff(_catalog(request), query)


@router.post("/calculations", response_model=TariffCalculationResponse)
def create_tariff_calculation(
    request: Request,
    body: TariffCalculationRequest,
) -> TariffCalculationResponse:
    return calculate_tariff(_catalog(request), body)
