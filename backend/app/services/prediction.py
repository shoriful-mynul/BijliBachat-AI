"""Household consumption forecast. A partial tariff is not a payable bill."""

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.common import TrustStatus
from app.schemas.meter_api import LedgerReading
from app.schemas.prediction import (
    BillCostView,
    BudgetValidationRequest,
    BudgetValidationResponse,
    ConsumptionForecastRequest,
    ConsumptionForecastResponse,
    ForecastPoint,
    QuantityView,
    TargetComparisonView,
)
from app.schemas.tariff import TariffCalculationRequest, TariffResolutionQuery
from app.services.meter_validation import _elapsed_days, _meter_key
from app.services.tariff_engine import calculate_tariff, resolve_tariff
from app.tariffs.loader import TariffCatalog
from app.tariffs.models import TariffConfig

_KWH = Decimal("0.001")
_MIN_READINGS = 3
_MIN_DAYS = Decimal(7)
_BUDGET_LIMITATION = (
    "This budget is a figure you entered. It is not a tariff and it is not saved on the server. "
    "This browser can keep it. Another device cannot."
)
_NO_PAYABLE = (
    "A payable bill cannot be projected. Missing tariff components are not treated as zero, "
    "and an energy or fixed charge is not used as the bill. Consumption can still be forecast."
)


def validate_budget(request: BudgetValidationRequest) -> BudgetValidationResponse:
    return BudgetValidationResponse(
        monthly_budget_pkr=_money(request.monthly_budget_pkr),
        monthly_kwh_target=_kwh(request.monthly_kwh_target),
        limitation=_BUDGET_LIMITATION,
    )


def forecast_consumption(catalog: TariffCatalog, request: ConsumptionForecastRequest) -> ConsumptionForecastResponse:
    readings = sorted(
        (item for item in request.readings if _meter_key(item.meter_reference) == _meter_key(request.meter_reference)),
        key=lambda item: item.read_at,
    )
    history = _history_gaps(readings)
    cycle = _cycle_gaps(request, readings)
    average = _average(readings, history)
    cycle_consumption = _cycle_consumption(request, readings, history, cycle)
    forecast_ready = not history and not cycle
    additional, projected, remaining = _project(readings, request, cycle_consumption, forecast_ready)
    bill = _bill_cost(catalog, request, projected if forecast_ready else None)
    return ConsumptionForecastResponse(
        forecast_status="estimated" if forecast_ready else "unavailable",
        cycle_consumption_kwh=cycle_consumption,
        average_daily_kwh=average,
        projected_additional_kwh=additional,
        projected_cycle_kwh=projected,
        observation_period=_period(readings) if readings else None,
        observation_days=_kwh(_elapsed_days(readings[0].read_at, readings[-1].read_at)) if len(readings) >= 2 else None,
        remaining_days=str(remaining) if remaining is not None else None,
        billing_cycle_started_on=request.cycle_started_on,
        billing_cycle_ends_on=request.cycle_ends_on,
        assumptions=_assumptions(),
        missing_inputs=[*history, *cycle],
        limitations=[
            "Checkpoints are readings you submitted. They are not a live meter feed.",
            "This API does not keep the checkpoints, the budget, or the forecast.",
            "No accuracy percentage is calculated.",
            _NO_PAYABLE,
        ],
        series=_series(readings, request, projected) if forecast_ready else [],
        bill_cost=bill,
        budget_comparison=_budget_comparison(request, bill),
        target_comparison=_target_comparison(request, projected if forecast_ready else None),
        monthly_budget_pkr=_money(request.monthly_budget_pkr),
        monthly_kwh_target=_kwh(request.monthly_kwh_target),
    )


def _history_gaps(readings: list[LedgerReading]) -> list[str]:
    gaps: list[str] = []
    if len(readings) < _MIN_READINGS:
        gaps.append("At least three checkpoints from the same meter are required.")
    if any(later.read_at <= earlier.read_at for earlier, later in zip(readings, readings[1:], strict=False)):
        gaps.append("Checkpoints must be in strict time order.")
    if any(later.register_kwh < earlier.register_kwh for earlier, later in zip(readings, readings[1:], strict=False)):
        gaps.append("A register decrease was found. The forecast was not adjusted.")
    if len(readings) >= 2 and _elapsed_days(readings[0].read_at, readings[-1].read_at) < _MIN_DAYS:
        gaps.append("The checkpoints span fewer than seven complete days.")
    return gaps


def _cycle_gaps(request: ConsumptionForecastRequest, readings: list[LedgerReading]) -> list[str]:
    gaps: list[str] = []
    if request.cycle_started_on is None or request.cycle_ends_on is None:
        gaps.append("Billing-cycle start and end dates are required.")
    elif request.cycle_ends_on < request.cycle_started_on:
        gaps.append("The billing-cycle end is earlier than its start.")
    if request.cycle_start_register_kwh is None:
        gaps.append("The meter register at the start of the cycle is required.")
    if not readings:
        gaps.append("A checkpoint inside the billing cycle is required.")
        return gaps
    latest = readings[-1]
    if request.cycle_started_on and request.cycle_ends_on and request.cycle_ends_on >= request.cycle_started_on:
        if latest.read_at.date() < request.cycle_started_on or latest.read_at.date() > request.cycle_ends_on:
            gaps.append("The latest checkpoint is outside the stated billing cycle.")
        if request.as_of.date() < request.cycle_started_on:
            gaps.append("The stated moment is before the billing cycle starts.")
        if (request.cycle_ends_on - request.as_of.date()).days <= 0:
            gaps.append("No days remain before the billing-cycle end.")
    if (
        request.cycle_start_register_kwh is not None
        and latest.register_kwh < request.cycle_start_register_kwh
    ):
        gaps.append("The latest register is below the cycle-start register. Consumption was not invented.")
    return gaps


def _average(readings: list[LedgerReading], history: list[str]) -> QuantityView:
    if history or len(readings) < 2:
        return _unavailable("Average daily use needs three checkpoints from one meter across at least seven complete days, with no register decrease.")
    elapsed = _elapsed_days(readings[0].read_at, readings[-1].read_at)
    if elapsed <= 0:
        return _unavailable("Average daily use was not calculated because no time passed between the checkpoints.")
    pace = (readings[-1].register_kwh - readings[0].register_kwh) / elapsed
    return QuantityView(
        value=_kwh(pace),
        trust_status=TrustStatus.CALCULATED,
        detail=(
            f"Calculated from the earliest and latest checkpoints, {_period(readings)}. "
            f"That span is {_kwh(elapsed)} days."
        ),
    )


def _cycle_consumption(
    request: ConsumptionForecastRequest,
    readings: list[LedgerReading],
    history: list[str],
    cycle: list[str],
) -> QuantityView:
    blocking = {
        "Billing-cycle start and end dates are required.",
        "The billing-cycle end is earlier than its start.",
        "The meter register at the start of the cycle is required.",
        "A checkpoint inside the billing cycle is required.",
        "The latest checkpoint is outside the stated billing cycle.",
        "The latest register is below the cycle-start register. Consumption was not invented.",
    }
    if any("register decrease" in item for item in history) or any(item in blocking for item in cycle):
        return _unavailable("Cycle consumption needs an explicit start register and a later checkpoint inside the same cycle.")
    if request.cycle_start_register_kwh is None or not readings:
        return _unavailable("Cycle consumption needs an explicit start register and a later checkpoint inside the same cycle.")
    used = readings[-1].register_kwh - request.cycle_start_register_kwh
    if used < 0:
        return _unavailable("Cycle consumption was not calculated because the register is below the cycle start.")
    return QuantityView(
        value=_kwh(used),
        trust_status=TrustStatus.CALCULATED,
        detail="Calculated from the cycle-start register you supplied and the latest checkpoint. An earlier checkpoint was not used as the cycle start.",
    )


def _project(
    readings: list[LedgerReading],
    request: ConsumptionForecastRequest,
    cycle_consumption: QuantityView,
    ready: bool,
) -> tuple[QuantityView, QuantityView, int | None]:
    if not ready or cycle_consumption.value is None or not readings or request.cycle_ends_on is None:
        blank = _unavailable("The consumption forecast is unavailable until the missing inputs are supplied.")
        return blank, blank, None
    elapsed = _elapsed_days(readings[0].read_at, readings[-1].read_at)
    pace = (readings[-1].register_kwh - readings[0].register_kwh) / elapsed
    remaining = (request.cycle_ends_on - request.as_of.date()).days
    additional = pace * Decimal(remaining)
    if additional < 0 or request.cycle_start_register_kwh is None:
        blank = _unavailable("A negative consumption forecast was not returned.")
        return blank, blank, None
    exact_cycle = readings[-1].register_kwh - request.cycle_start_register_kwh
    projected = exact_cycle + additional
    return (
        QuantityView(
            value=_kwh(additional),
            trust_status=TrustStatus.ESTIMATED,
            detail=f"Estimated as the observed daily pace multiplied by {remaining} remaining days. A 30-day month was not assumed.",
        ),
        QuantityView(
            value=_kwh(projected),
            trust_status=TrustStatus.ESTIMATED,
            detail="Estimated as cycle consumption so far plus the estimated additional consumption.",
        ),
        remaining,
    )


def _series(
    readings: list[LedgerReading],
    request: ConsumptionForecastRequest,
    projected: QuantityView,
) -> list[ForecastPoint]:
    if projected.value is None or request.cycle_start_register_kwh is None or request.cycle_ends_on is None:
        return []
    if request.cycle_started_on is None:
        return []
    points: list[ForecastPoint] = []
    for reading in readings:
        if request.cycle_started_on <= reading.read_at.date() <= request.cycle_ends_on:
            used = reading.register_kwh - request.cycle_start_register_kwh
            if used < 0:
                continue
            points.append(
                ForecastPoint(
                    on=reading.read_at.date(),
                    kwh=_kwh(used),
                    kind="observed",
                    trust_status=TrustStatus.CALCULATED,
                    label=reading.read_at.date().isoformat(),
                )
            )
    points.append(
        ForecastPoint(
            on=request.cycle_ends_on,
            kwh=projected.value,
            kind="estimated",
            trust_status=TrustStatus.ESTIMATED,
            label="Billing-cycle end",
        )
    )
    return points


def _bill_cost(
    catalog: TariffCatalog,
    request: ConsumptionForecastRequest,
    projected: QuantityView | None,
) -> BillCostView:
    if not request.provider_code or not request.consumer_category or not request.tariff_type or not request.billing_date:
        return BillCostView(
            trust_status=TrustStatus.UNAVAILABLE,
            reason="A payable amount was not calculated because the tariff scope was not submitted. Consumption can still be forecast.",
            missing_components=["tariff scope"],
            comparable_with_budget=False,
        )
    resolved = resolve_tariff(
        catalog,
        TariffResolutionQuery(
            provider_code=request.provider_code,
            consumer_category=request.consumer_category,
            tariff_type=request.tariff_type,
            eligibility=request.eligibility,
            billing_date=request.billing_date,
        ),
    )
    config = _matched_config(catalog, resolved.configuration.config_id if resolved.configuration else None)
    if config is None:
        return BillCostView(
            trust_status=TrustStatus.UNAVAILABLE,
            reason=resolved.reason,
            missing_components=resolved.missing_inputs or ["verified tariff configuration"],
            comparable_with_budget=False,
        )
    missing = _missing_payable_components(config)
    if missing or projected is None or projected.value is None:
        return BillCostView(
            trust_status=TrustStatus.UNAVAILABLE,
            reason=_NO_PAYABLE if missing else "A payable amount was not calculated because the consumption forecast is unavailable.",
            missing_components=missing,
            comparable_with_budget=False,
        )
    result = calculate_tariff(
        catalog,
        TariffCalculationRequest(
            provider_code=request.provider_code,
            consumer_category=request.consumer_category or "",
            tariff_type=request.tariff_type,  # type: ignore[arg-type]
            eligibility=request.eligibility,
            billing_date=request.billing_date,  # type: ignore[arg-type]
            consumption_kwh=projected.value,
        ),
    )
    if result.final_amount is None:
        return BillCostView(
            trust_status=TrustStatus.UNAVAILABLE,
            reason=result.reason,
            missing_components=result.blocking_components or result.missing_inputs or ["payable total"],
            comparable_with_budget=False,
        )
    return BillCostView(
        value=f"{result.final_amount:.2f}",
        trust_status=TrustStatus.ESTIMATED,
        reason="Estimated by applying the complete verified tariff to the estimated cycle consumption. This is not a confirmed bill.",
        missing_components=[],
        comparable_with_budget=request.monthly_budget_pkr is not None,
    )


def _budget_comparison(request: ConsumptionForecastRequest, bill: BillCostView) -> BillCostView:
    if bill.value is None or request.monthly_budget_pkr is None or not bill.comparable_with_budget:
        detail = "The PKR budget cannot be compared because a complete payable bill projection is unavailable."
        if request.monthly_budget_pkr is None:
            detail = "No monthly budget has been entered, and a payable bill projection is unavailable."
        return BillCostView(
            trust_status=TrustStatus.UNAVAILABLE,
            reason=detail,
            missing_components=bill.missing_components,
            comparable_with_budget=False,
        )
    projected = Decimal(bill.value)
    if projected > request.monthly_budget_pkr:
        reason = "The estimated payable amount is higher than the budget you entered."
    elif projected < request.monthly_budget_pkr:
        reason = "The estimated payable amount is lower than the budget you entered."
    else:
        reason = "The estimated payable amount matches the budget you entered."
    return BillCostView(
        value=bill.value,
        trust_status=TrustStatus.ESTIMATED,
        reason=reason,
        missing_components=[],
        comparable_with_budget=True,
    )


def _target_comparison(request: ConsumptionForecastRequest, projected: QuantityView | None) -> TargetComparisonView:
    if request.monthly_kwh_target is None:
        return TargetComparisonView(
            status="unavailable",
            direction="unavailable",
            trust_status=TrustStatus.UNAVAILABLE,
            detail="No monthly consumption target was entered. A tariff slab is not used as that target.",
        )
    if projected is None or projected.value is None:
        return TargetComparisonView(
            status="unavailable",
            direction="unavailable",
            target_kwh=_kwh(request.monthly_kwh_target),
            trust_status=TrustStatus.UNAVAILABLE,
            detail="The consumption target cannot be compared until the forecast is available.",
        )
    projected_value = Decimal(projected.value)
    target = request.monthly_kwh_target
    difference = projected_value - target
    if difference > 0:
        direction = "higher"
        detail = "The estimated cycle consumption is higher than the consumption target you entered."
    elif difference < 0:
        direction = "lower"
        detail = "The estimated cycle consumption is lower than the consumption target you entered."
    else:
        direction = "equal"
        detail = "The estimated cycle consumption matches the consumption target you entered."
    return TargetComparisonView(
        status="estimated",
        direction=direction,
        projected_cycle_kwh=projected.value,
        target_kwh=_kwh(target),
        difference_kwh=_kwh(difference),
        trust_status=TrustStatus.ESTIMATED,
        detail=detail,
    )


def _missing_payable_components(config: TariffConfig) -> list[str]:
    missing: list[str] = []
    if config.verification_status != "verified" or config.synthetic:
        missing.append("verified production tariff")
    if config.fixed_charge.state in {"unavailable", "needs_verification"}:
        missing.append(config.fixed_charge.reason)
    if config.minimum_charge.state in {"unavailable", "needs_verification"}:
        missing.append(config.minimum_charge.reason)
    for item in config.adjustments:
        if item.required_for_payable and item.state != "applicable_verified":
            missing.append(item.label)
    return missing


def _matched_config(catalog: TariffCatalog, config_id: str | None) -> TariffConfig | None:
    if config_id is None:
        return None
    for config in catalog.configs:
        if config.config_id == config_id:
            return config
    return None


def _assumptions() -> list[str]:
    return [
        "The daily pace is the change from the earliest checkpoint to the latest checkpoint for this meter, divided by the exact days between those timestamps.",
        "A complete day is 86400 seconds. The forecast needs at least seven complete days.",
        "Remaining days are the midnights from the stated date until the cycle end date.",
        "The projection assumes that pace continues. It is an estimate, not a bill and not a meter reading.",
    ]


def _period(readings: list[LedgerReading]) -> str:
    return f"{readings[0].read_at.date().isoformat()} to {readings[-1].read_at.date().isoformat()}"


def _unavailable(detail: str) -> QuantityView:
    return QuantityView(value=None, trust_status=TrustStatus.UNAVAILABLE, detail=detail)


def _kwh(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(_KWH, rounding=ROUND_HALF_UP):.3f}"


def _money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
