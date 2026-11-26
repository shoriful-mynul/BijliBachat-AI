"""Thin prediction routes. Forecast maths live in the service."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.prediction import (
    BudgetValidationRequest,
    BudgetValidationResponse,
    ConsumptionForecastRequest,
    ConsumptionForecastResponse,
)
from app.services.prediction import forecast_consumption, validate_budget

router = APIRouter(prefix="/predictions")


def _error(status: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


@router.post("/budget", response_model=BudgetValidationResponse)
def check_budget(body: BudgetValidationRequest) -> BudgetValidationResponse | JSONResponse:
    if body.monthly_budget_pkr is None and body.monthly_kwh_target is None:
        return _error(422, ErrorCode.INVALID_REQUEST, "Enter a monthly budget or a consumption target.")
    return validate_budget(body)


@router.post("/consumption", response_model=ConsumptionForecastResponse)
def calculate_consumption_forecast(request: Request, body: ConsumptionForecastRequest) -> ConsumptionForecastResponse:
    return forecast_consumption(request.app.state.tariff_catalog, body)
