"""Appliance consumption and what-if comparisons.

Displayed kWh are quantized after the exact Decimal calculation.
A partial tariff is not turned into a rupee saving.
"""

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.appliance import (
    ActionItem,
    ActionPlanResponse,
    ApplianceChange,
    ApplianceLine,
    ApplianceSpec,
    ConsumptionRequest,
    ConsumptionResponse,
    PkrImpact,
    ScenarioRequest,
    ScenarioResponse,
)
from app.schemas.common import TrustStatus
from app.tariffs.loader import TariffCatalog
from app.tariffs.models import TariffConfig

_KWH = Decimal("0.001")
_PERCENT = Decimal("0.01")
_ASSUMPTIONS = [
    "Daily use on a day the appliance runs is rated watts times quantity times hours, divided by 1000.",
    "When days per week are omitted, those hours apply on every day of the selected period.",
    "When days per week are entered, period use multiplies by that count divided by 7.",
    "Displayed kilowatt-hours are rounded half-up to 0.001 after the exact calculation. Intermediate results are not rounded.",
    "A scenario is a schedule you proposed. It is not a measured saving.",
]
_PKR_REASON = (
    "PKR savings are unavailable. No loaded tariff file contains every component of a payable bill. "
    "Missing components are not treated as zero, and no per-unit price is assumed."
)


def calculate_consumption(catalog: TariffCatalog, request: ConsumptionRequest) -> ConsumptionResponse:
    if not request.appliances:
        return ConsumptionResponse(
            status="unavailable",
            appliances=[],
            assumptions=_ASSUMPTIONS,
            limitations=_limitations(),
            pkr_impact=_pkr(catalog),
        )
    exact = [_average_daily(item) for item in request.appliances]
    total = sum(exact, start=Decimal(0))
    lines = [
        _line(item, daily, request.days, total)
        for item, daily in zip(request.appliances, exact, strict=True)
    ]
    period = None
    if request.days is not None:
        period = _q(sum((_period(item, request.days) for item in request.appliances), start=Decimal(0)))
    return ConsumptionResponse(
        status="calculated",
        total_daily_kwh=_q(total),
        total_period_kwh=period,
        days=request.days,
        appliances=lines,
        assumptions=_ASSUMPTIONS,
        limitations=_limitations(request.days is None),
        pkr_impact=_pkr(catalog),
    )


def compare_scenario(catalog: TariffCatalog, request: ScenarioRequest) -> ScenarioResponse:
    pairs = _pairs(request)
    if not pairs:
        return ScenarioResponse(
            status="unavailable",
            direction="unavailable",
            days=request.days,
            appliances=[],
            assumptions=_ASSUMPTIONS,
            limitations=_limitations(),
            pkr_impact=_pkr(catalog),
        )
    changes: list[ApplianceChange] = []
    baseline_total = Decimal(0)
    scenario_total = Decimal(0)
    for baseline, proposed in pairs:
        base = _period(baseline, request.days)
        proposed_use = _period(proposed, request.days)
        baseline_total += base
        scenario_total += proposed_use
        changes.append(_change(baseline, proposed, base, proposed_use))
    return _scenario_response(catalog, request.days, baseline_total, scenario_total, changes)


def build_action_plan(catalog: TariffCatalog, request: ScenarioRequest) -> ActionPlanResponse:
    comparison = compare_scenario(catalog, request)
    actions: list[ActionItem] = []
    paired = {baseline.id: (baseline, proposed) for baseline, proposed in _pairs(request)}
    for change in comparison.appliances:
        if change.direction == "unchanged":
            continue
        baseline, proposed = paired[change.id]
        actions.append(
            ActionItem(
                title=_title(change.direction, baseline.name),
                appliance_id=baseline.id,
                appliance_name=baseline.name,
                baseline_assumption=_schedule(baseline),
                proposed_assumption=_schedule(proposed),
                difference_kwh=change.difference_kwh,
                direction=change.direction,  # type: ignore[arg-type]
                trust_status=TrustStatus.ESTIMATED,
                explanation=(
                    f"{change.detail} This is a scenario, not a measured saving and not a rupee amount."
                ),
            )
        )
    if not actions:
        detail = (
            "No proposed change was entered, so no action shows an estimated difference."
            if comparison.status == "estimated"
            else "Add an appliance before an action can be estimated."
        )
        return ActionPlanResponse(
            status="unavailable",
            days=request.days,
            actions=[],
            detail=detail,
            assumptions=_ASSUMPTIONS,
            limitations=_limitations(),
            pkr_impact=_pkr(catalog),
        )
    return ActionPlanResponse(
        status="estimated",
        days=request.days,
        actions=actions,
        detail="These actions repeat the scenario you entered. They are not a ranked list and not a measured saving.",
        assumptions=_ASSUMPTIONS,
        limitations=_limitations(),
        pkr_impact=_pkr(catalog),
    )


def _pairs(request: ScenarioRequest) -> list[tuple[ApplianceSpec, ApplianceSpec]]:
    proposed = {item.id: item for item in request.proposed}
    return [(item, proposed[item.id]) for item in request.baseline]


def _average_daily(item: ApplianceSpec) -> Decimal:
    running = item.rated_watts * Decimal(item.quantity) * item.operating_hours_per_day / Decimal(1000)
    if item.operating_days_per_week is None:
        return running
    return running * Decimal(item.operating_days_per_week) / Decimal(7)


def _period(item: ApplianceSpec, days: int) -> Decimal:
    return _average_daily(item) * Decimal(days)


def _line(item: ApplianceSpec, daily: Decimal, days: int | None, total: Decimal) -> ApplianceLine:
    share = None
    if total > 0:
        share = _percent(daily / total * Decimal(100))
    period = _q(_period(item, days)) if days is not None else None
    return ApplianceLine(
        id=item.id,
        name=item.name,
        rated_watts=_watts(item.rated_watts),
        quantity=item.quantity,
        operating_hours_per_day=_hours(item.operating_hours_per_day),
        operating_days_per_week=item.operating_days_per_week,
        daily_kwh=_q(daily),
        period_kwh=period,
        share_percent=share,
        trust_status=TrustStatus.CALCULATED,
        detail=_schedule(item),
    )


def _change(
    baseline: ApplianceSpec,
    proposed: ApplianceSpec,
    base: Decimal,
    proposed_use: Decimal,
) -> ApplianceChange:
    saved = base - proposed_use
    if saved > 0:
        direction = "reduced"
        detail = f"Over this period the proposal uses {_q(saved)} kWh less than the schedule you entered."
    elif saved < 0:
        direction = "increased"
        detail = f"Over this period the proposal uses {_q(abs(saved))} kWh more than the schedule you entered."
    else:
        direction = "unchanged"
        detail = "The proposal uses the same electricity as the schedule you entered."
    percentage = None if base <= 0 else _percent(saved / base * Decimal(100))
    return ApplianceChange(
        id=baseline.id,
        name=baseline.name,
        direction=direction,
        baseline_kwh=_q(base),
        scenario_kwh=_q(proposed_use),
        difference_kwh=_q(abs(saved)),
        percentage_difference=percentage,
        trust_status=TrustStatus.ESTIMATED,
        detail=detail,
    )


def _scenario_response(
    catalog: TariffCatalog,
    days: int,
    baseline_total: Decimal,
    scenario_total: Decimal,
    changes: list[ApplianceChange],
) -> ScenarioResponse:
    saved = baseline_total - scenario_total
    if saved > 0:
        direction = "reduced"
    elif saved < 0:
        direction = "increased"
    else:
        direction = "unchanged"
    percentage = None if baseline_total <= 0 else _percent(saved / baseline_total * Decimal(100))
    return ScenarioResponse(
        status="estimated",
        direction=direction,
        days=days,
        baseline_kwh=_q(baseline_total),
        scenario_kwh=_q(scenario_total),
        difference_kwh=_q(abs(saved)),
        percentage_difference=percentage,
        appliances=changes,
        assumptions=_ASSUMPTIONS,
        limitations=_limitations(),
        pkr_impact=_pkr(catalog),
    )


def _schedule(item: ApplianceSpec) -> str:
    week = (
        f"{item.operating_days_per_week} days each week"
        if item.operating_days_per_week is not None
        else "every day of the period"
    )
    watts = _watts(item.rated_watts)
    hours = _hours(item.operating_hours_per_day)
    return (
        f"{item.quantity} × {item.name}, {watts} W, {hours} hours on a day it runs, {week}. "
        "The wattage was entered by the household."
    )


def _title(direction: str, name: str) -> str:
    if direction == "reduced":
        return f"Use {name} less in this scenario"
    return f"Use {name} more in this scenario"


def _pkr(catalog: TariffCatalog) -> PkrImpact:
    missing: list[str] = []
    complete = False
    for config in catalog.configs:
        gaps = _missing_payable(config)
        if not gaps:
            complete = True
        for label in gaps:
            if label not in missing:
                missing.append(label)
    if complete:
        reason = (
            "A complete payable file is loaded, but this request has no tariff scope. "
            "No rupee saving was calculated."
        )
    else:
        reason = _PKR_REASON
    return PkrImpact(
        value=None,
        trust_status=TrustStatus.UNAVAILABLE,
        reason=reason,
        missing_components=missing,
        comparable=False,
    )


def _missing_payable(config: TariffConfig) -> list[str]:
    missing: list[str] = []
    if config.synthetic or config.verification_status != "verified":
        missing.append("verified production tariff")
    for item in config.adjustments:
        if item.required_for_payable and item.state != "applicable_verified":
            missing.append(item.label)
    return missing


def _limitations(days_missing: bool = False) -> list[str]:
    notes = [
        "This API does not keep appliance records.",
        "PKR savings are not calculated from a partial tariff.",
    ]
    if days_missing:
        notes.append("Period consumption needs the number of days. A 30-day month was not assumed.")
    return notes


def _q(value: Decimal) -> str:
    return f"{value.quantize(_KWH, rounding=ROUND_HALF_UP):.3f}"


def _percent(value: Decimal) -> str:
    return f"{value.quantize(_PERCENT, rounding=ROUND_HALF_UP):.2f}"


def _watts(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP):.3f}"


def _hours(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP):.3f}"
