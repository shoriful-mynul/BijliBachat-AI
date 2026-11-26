"""Thin history routes. Comparisons live in the service."""

from fastapi import APIRouter, Request

from app.schemas.history import (
    BaselineComparisonRequest,
    BaselineComparisonResponse,
    CycleCompareRequest,
    CycleCompareResponse,
    CycleValidateRequest,
    CycleValidateResponse,
    ForecastComparisonRequest,
    ForecastComparisonResponse,
    ForecastSnapshotRequest,
    ForecastSnapshotResponse,
    InsightRequest,
    InsightResponse,
)
from app.services.history import (
    build_insights,
    compare_baseline,
    compare_cycles,
    compare_forecast,
    save_forecast_snapshot,
    validate_cycle,
)

router = APIRouter(prefix="/history")


@router.post("/cycles/validate", response_model=CycleValidateResponse)
def validate_history_cycle(request: Request, body: CycleValidateRequest) -> CycleValidateResponse:
    return validate_cycle(request.app.state.tariff_catalog, body)


@router.post("/cycles/compare", response_model=CycleCompareResponse)
def compare_history_cycles(request: Request, body: CycleCompareRequest) -> CycleCompareResponse:
    return compare_cycles(request.app.state.tariff_catalog, body)


@router.post("/forecast-snapshots", response_model=ForecastSnapshotResponse)
def create_forecast_snapshot(request: Request, body: ForecastSnapshotRequest) -> ForecastSnapshotResponse:
    return save_forecast_snapshot(request.app.state.tariff_catalog, body)


@router.post("/forecast-comparisons", response_model=ForecastComparisonResponse)
def compare_saved_forecast(request: Request, body: ForecastComparisonRequest) -> ForecastComparisonResponse:
    return compare_forecast(request.app.state.tariff_catalog, body)


@router.post("/baseline-comparisons", response_model=BaselineComparisonResponse)
def compare_entered_baseline(request: Request, body: BaselineComparisonRequest) -> BaselineComparisonResponse:
    return compare_baseline(request.app.state.tariff_catalog, body)


@router.post("/insights", response_model=InsightResponse)
def history_insights(request: Request, body: InsightRequest) -> InsightResponse:
    return build_insights(request.app.state.tariff_catalog, body)
