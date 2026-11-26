"""Thin appliance routes. Consumption maths live in the service."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.appliance import (
    ActionPlanResponse,
    ConsumptionRequest,
    ConsumptionResponse,
    ScenarioRequest,
    ScenarioResponse,
)
from app.schemas.errors import ErrorCode, ErrorResponse
from app.services.appliances import build_action_plan, calculate_consumption, compare_scenario

router = APIRouter(prefix="/appliances")


def _error(message: str) -> JSONResponse:
    body = ErrorResponse(code=ErrorCode.INVALID_REQUEST, message=message[:300])
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


@router.post("/consumption", response_model=ConsumptionResponse)
def consumption(request: Request, body: ConsumptionRequest) -> ConsumptionResponse:
    return calculate_consumption(request.app.state.tariff_catalog, body)


@router.post("/scenarios", response_model=ScenarioResponse)
def scenarios(request: Request, body: ScenarioRequest) -> ScenarioResponse | JSONResponse:
    try:
        return compare_scenario(request.app.state.tariff_catalog, body)
    except ValueError as exc:
        return _error(str(exc))


@router.post("/action-plan", response_model=ActionPlanResponse)
def action_plan(request: Request, body: ScenarioRequest) -> ActionPlanResponse | JSONResponse:
    try:
        return build_action_plan(request.app.state.tariff_catalog, body)
    except ValueError as exc:
        return _error(str(exc))
