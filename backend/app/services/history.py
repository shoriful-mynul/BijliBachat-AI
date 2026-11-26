"""Measured history. Forecasts stay estimates, and a partial tariff is not a saving."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from app.schemas.common import TrustStatus
from app.schemas.history import (
    BaselineComparisonRequest,
    BaselineComparisonResponse,
    CycleCompareRequest,
    CycleCompareResponse,
    CycleInput,
    CycleValidateRequest,
    CycleValidateResponse,
    CycleView,
    ForecastComparisonRequest,
    ForecastComparisonResponse,
    ForecastSnapshotRequest,
    ForecastSnapshotResponse,
    ForecastSnapshotView,
    InsightItem,
    InsightRequest,
    InsightResponse,
    PkrImpact,
    SnapshotInput,
    StoredCycleRef,
)
from app.services.meter_validation import _elapsed_days, _meter_key
from app.services.prediction import forecast_consumption
from app.tariffs.loader import TariffCatalog
from app.tariffs.models import TariffConfig

_KWH = Decimal("0.001")
_PERCENT = Decimal("0.01")
_DURATION_TOLERANCE = Decimal(1)
_METHOD = "checkpoint-pace-v1"
_ASSUMPTIONS = [
    "Actual cycle use is the ending register minus the starting register.",
    "Duration is the exact elapsed time between the two checkpoint timestamps, divided by 86400 seconds. It is not a count of calendar dates.",
    "Average daily use is actual cycle use divided by that elapsed time.",
    "Cycles are different lengths when their elapsed times differ by more than one day. Totals are still shown, and average daily use is the comparison to read.",
    "A saved forecast is the estimate returned earlier. It is not actual use, and this comparison is not a model accuracy score.",
    "A kWh target is a figure the household entered. It is not a verified baseline and not a rupee amount.",
]
_PKR_REASON = (
    "PKR savings are unavailable. No loaded tariff file contains every component of a payable bill. "
    "Missing components are not treated as zero, and no per-unit price is assumed."
)
_LIMITS = [
    "This API does not keep cycles, forecasts, or targets.",
    "A lower kWh figure is measured use. It is not proof that an appliance action caused it, and it is not a rupee saving.",
    "PKR savings are not calculated from a partial tariff.",
]


def validate_cycle(catalog: TariffCatalog, request: CycleValidateRequest) -> CycleValidateResponse:
    start = _find(request.readings, request.start_checkpoint_id)
    end = _find(request.readings, request.end_checkpoint_id)
    if start is None or end is None:
        return _rejected_cycle(
            catalog,
            "unavailable",
            "A selected checkpoint is not in the confirmed list. An unconfirmed draft was not used.",
        )
    if request.start_checkpoint_id == request.end_checkpoint_id:
        return _rejected_cycle(catalog, "rejected", "Choose two different checkpoints.")
    if not _same_meter(start.meter_reference, end.meter_reference) or not _meter_key(start.meter_reference):
        return _rejected_cycle(catalog, "rejected", "Both checkpoints must belong to the same recorded meter.")
    if end.read_at <= start.read_at:
        return _rejected_cycle(catalog, "rejected", "The ending checkpoint must be later than the starting checkpoint.")
    if end.register_kwh < start.register_kwh:
        return _rejected_cycle(catalog, "rejected", "The ending register is lower than the starting register. Consumption was not invented.")
    others = [item for item in request.existing_cycles if item.id != request.ignore_cycle_id]
    if any(item.id == request.cycle_id for item in others):
        return _rejected_cycle(catalog, "rejected", "A cycle with this id already exists.")
    if any(
        item.start_checkpoint_id == start.id and item.end_checkpoint_id == end.id
        for item in others
    ):
        return _rejected_cycle(catalog, "rejected", "This pair of checkpoints is already a cycle.")
    if any(_overlaps(start.read_at, end.read_at, item) and _same_meter(start.meter_reference, item.meter_reference) for item in others):
        return _rejected_cycle(
            catalog,
            "rejected",
            "This period overlaps another cycle for the same meter. Touching at an endpoint is allowed.",
        )
    view = _view_from_checkpoints(request.cycle_id, start, end)
    return CycleValidateResponse(
        status="accepted",
        cycle=view,
        detail=view.detail,
        assumptions=_ASSUMPTIONS,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def compare_cycles(catalog: TariffCatalog, request: CycleCompareRequest) -> CycleCompareResponse:
    earlier_problem = _cycle_problem(request.earlier)
    later_problem = _cycle_problem(request.later)
    if earlier_problem or later_problem:
        return _blank_compare(catalog, earlier_problem or later_problem or "The cycles could not be compared.")
    if request.earlier.id == request.later.id:
        return _blank_compare(catalog, "Choose two different cycles.")
    if not _same_meter(request.earlier.meter_reference, request.later.meter_reference):
        return _blank_compare(catalog, "A comparison is unavailable because the cycles are not from the same meter.")
    if request.earlier.ended_at > request.later.ended_at:
        return _blank_compare(catalog, "The first cycle ends after the second. Choose them in time order.")
    if _periods_overlap(request.earlier.started_at, request.earlier.ended_at, request.later.started_at, request.later.ended_at):
        return _blank_compare(
            catalog,
            "These periods overlap, so they were not compared as separate cycles. Touching at an endpoint is allowed.",
        )
    earlier = _view_from_input(request.earlier)
    later = _view_from_input(request.later)
    if earlier is None or later is None:
        return _blank_compare(catalog, "One cycle does not have a later ending register and a later timestamp.")
    return _comparison(catalog, earlier, later, _exact_actual(request.earlier), _exact_actual(request.later), _elapsed(request.earlier), _elapsed(request.later))


def save_forecast_snapshot(catalog: TariffCatalog, request: ForecastSnapshotRequest) -> ForecastSnapshotResponse:
    forecast = forecast_consumption(catalog, request)
    projected = forecast.projected_cycle_kwh.value
    readings = sorted(
        (item for item in request.readings if _meter_key(item.meter_reference) == _meter_key(request.meter_reference)),
        key=lambda item: item.read_at,
    )
    if forecast.forecast_status != "estimated" or projected is None or not readings or request.cycle_started_on is None or request.cycle_ends_on is None or request.cycle_start_register_kwh is None:
        return ForecastSnapshotResponse(
            status="unavailable",
            snapshot=None,
            detail="A snapshot is saved only when the forecast is available. This forecast was not changed.",
            limitations=_LIMITS,
            pkr_impact=_pkr(catalog),
        )
    latest = readings[-1]
    snapshot = ForecastSnapshotView(
        id=request.snapshot_id,
        meter_reference=request.meter_reference,
        created_at=request.as_of,
        cycle_started_on=request.cycle_started_on,
        cycle_ends_on=request.cycle_ends_on,
        cycle_start_register_kwh=_q(request.cycle_start_register_kwh),
        latest_register_kwh=_q(latest.register_kwh),
        latest_checkpoint_id=latest.id,
        projected_cycle_kwh=projected,
        reading_ids=[item.id for item in readings],
        assumptions=forecast.assumptions,
        detail="This is the estimate the forecast returned. Saving it did not change that calculation.",
    )
    return ForecastSnapshotResponse(
        status="estimated",
        snapshot=snapshot,
        detail=snapshot.detail,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def compare_forecast(catalog: TariffCatalog, request: ForecastComparisonRequest) -> ForecastComparisonResponse:
    cycle = _view_from_input(request.cycle)
    if cycle is None:
        return _blank_forecast(catalog, "Actual use is unavailable because the cycle checkpoints are not valid.")
    problem = _snapshot_match(request.snapshot, request.cycle)
    if problem:
        return _blank_forecast(catalog, problem)
    actual = _exact_actual(request.cycle)
    forecast = request.snapshot.projected_cycle_kwh
    difference = actual - forecast
    percentage = None if forecast <= 0 else _percent(difference / forecast * Decimal(100))
    if difference > 0:
        direction = "higher"
        sentence = f"Actual usage was {_q(difference)} kWh higher than your saved forecast."
    elif difference < 0:
        direction = "lower"
        sentence = f"Actual usage was {_q(abs(difference))} kWh lower than your saved forecast."
    else:
        direction = "equal"
        sentence = "Actual usage matched your saved forecast."
    return ForecastComparisonResponse(
        status="calculated",
        direction=direction,
        actual_kwh=_q(actual),
        forecast_kwh=_q(forecast),
        difference_kwh=_q(difference),
        absolute_difference_kwh=_q(abs(difference)),
        percentage_difference=percentage,
        actual_trust_status=TrustStatus.CALCULATED,
        forecast_trust_status=TrustStatus.ESTIMATED,
        difference_trust_status=TrustStatus.CALCULATED,
        detail=f"{sentence} This compares measured use with a previous estimate. It is not a model accuracy guarantee.",
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def compare_baseline(catalog: TariffCatalog, request: BaselineComparisonRequest) -> BaselineComparisonResponse:
    cycle = _view_from_input(request.cycle)
    if cycle is None:
        return _blank_baseline(catalog, "Measured use is unavailable, so it was not compared with the target.")
    if request.cycle_id != request.cycle.id:
        return _blank_baseline(catalog, "The target refers to a different cycle, so it was not compared.")
    actual = _exact_actual(request.cycle)
    target = request.target_kwh
    difference = actual - target
    percentage = None if target <= 0 else _percent(difference / target * Decimal(100))
    if difference > 0:
        direction = "higher"
    elif difference < 0:
        direction = "lower"
    else:
        direction = "equal"
    shown_target = _q(target)
    shown_actual = _q(actual)
    return BaselineComparisonResponse(
        status="calculated",
        direction=direction,
        actual_kwh=shown_actual,
        target_kwh=shown_target,
        difference_kwh=_q(difference),
        absolute_difference_kwh=_q(abs(difference)),
        percentage_difference=percentage,
        trust_status=TrustStatus.CALCULATED,
        detail=(
            f"Your entered target was {shown_target} kWh; measured consumption was {shown_actual} kWh. "
            "This target was entered by the household. It is not a verified historical baseline, and it is not a rupee saving."
        ),
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def build_insights(catalog: TariffCatalog, request: InsightRequest) -> InsightResponse:
    usable = [item for item in request.cycles if _view_from_input(item) is not None]
    usable.sort(key=lambda item: item.ended_at)
    latest_view = _view_from_input(usable[-1]) if usable else None
    if latest_view is None:
        return InsightResponse(
            status="unavailable",
            cycle_count=0,
            direction="unavailable",
            insights=[
                InsightItem(
                    code="insufficient",
                    title="Not enough history",
                    detail="Not enough historical data exists to identify a trend.",
                    trust_status=TrustStatus.UNAVAILABLE,
                )
            ],
            assumptions=_ASSUMPTIONS,
            limitations=_LIMITS,
            pkr_impact=_pkr(catalog),
        )
    previous = next((item for item in reversed(usable[:-1]) if _same_meter(item.meter_reference, usable[-1].meter_reference)), None)
    if previous is None:
        other_meter = any(not _same_meter(item.meter_reference, usable[-1].meter_reference) for item in usable[:-1])
        if other_meter:
            insight = InsightItem(
                code="meter_mismatch",
                title="Different meter",
                detail="A comparison is unavailable because the meter does not match.",
                trust_status=TrustStatus.UNAVAILABLE,
            )
        else:
            insight = InsightItem(
                code="insufficient",
                title="Not enough history",
                detail="Not enough historical data exists to identify a trend.",
                trust_status=TrustStatus.UNAVAILABLE,
            )
        return InsightResponse(
            status="unavailable",
            cycle_count=len(usable),
            latest_cycle_kwh=latest_view.actual_kwh,
            latest_average_daily_kwh=latest_view.average_daily_kwh,
            direction="unavailable",
            insights=[insight],
            assumptions=_ASSUMPTIONS,
            limitations=_LIMITS,
            pkr_impact=_pkr(catalog),
        )
    comparison = compare_cycles(catalog, CycleCompareRequest(earlier=previous, later=usable[-1]))
    insights = _insight_items(comparison)
    return InsightResponse(
        status="calculated" if comparison.status == "calculated" else "unavailable",
        cycle_count=len(usable),
        latest_cycle_kwh=latest_view.actual_kwh,
        latest_average_daily_kwh=latest_view.average_daily_kwh,
        direction=comparison.direction,
        insights=insights,
        assumptions=_ASSUMPTIONS,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def _comparison(
    catalog: TariffCatalog,
    earlier: CycleView,
    later: CycleView,
    earlier_exact: Decimal,
    later_exact: Decimal,
    earlier_elapsed: Decimal,
    later_elapsed: Decimal,
) -> CycleCompareResponse:
    comparable = abs(earlier_elapsed - later_elapsed) <= _DURATION_TOLERANCE
    warning = None
    if not comparable:
        warning = (
            "These cycles cover different lengths, so the totals are not a like-for-like comparison. "
            "Average daily use is the figure to compare."
        )
    total_difference = earlier_exact - later_exact
    earlier_avg = earlier_exact / earlier_elapsed
    later_avg = later_exact / later_elapsed
    average_difference = earlier_avg - later_avg
    if average_difference > 0:
        direction = "reduced"
        change = f"Average daily consumption decreased by {_q(average_difference)} kWh."
    elif average_difference < 0:
        direction = "increased"
        change = f"Average daily consumption increased by {_q(abs(average_difference))} kWh."
    else:
        direction = "unchanged"
        change = "No meaningful change was observed in average daily consumption."
    percentage = None
    if comparable and earlier_exact > 0:
        percentage = _percent(total_difference / earlier_exact * Decimal(100))
    elif earlier_avg > 0:
        percentage = _percent(average_difference / earlier_avg * Decimal(100))
    total_sentence = ""
    if comparable:
        if total_difference > 0:
            total_sentence = f" Your measured consumption was {_q(total_difference)} kWh lower than the previous cycle."
        elif total_difference < 0:
            total_sentence = f" Your measured consumption was {_q(abs(total_difference))} kWh higher than the previous cycle."
        else:
            total_sentence = " Measured consumption matched the previous cycle."
    return CycleCompareResponse(
        status="calculated",
        durations_comparable=comparable,
        duration_warning=warning,
        earlier=earlier,
        later=later,
        usage_difference_kwh=_q(total_difference),
        absolute_difference_kwh=_q(abs(total_difference)),
        percentage_difference=percentage,
        average_daily_difference_kwh=_q(average_difference),
        direction=direction,
        detail=f"{change}{total_sentence} This is measured use. It does not show that an appliance action caused the change.",
        assumptions=_ASSUMPTIONS,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def _insight_items(comparison: CycleCompareResponse) -> list[InsightItem]:
    if comparison.direction == "reduced":
        code = "decreased"
        title = "Average daily use decreased"
    elif comparison.direction == "increased":
        code = "increased"
        title = "Average daily use increased"
    elif comparison.direction == "unchanged":
        code = "unchanged"
        title = "No meaningful change"
    else:
        code = "insufficient"
        title = "Comparison unavailable"
    items = [
        InsightItem(
            code=code,
            title=title,
            detail=comparison.detail,
            trust_status=TrustStatus.CALCULATED if comparison.status == "calculated" else TrustStatus.UNAVAILABLE,
        )
    ]
    if comparison.duration_warning:
        items.append(
            InsightItem(
                code="duration_warning",
                title="Different cycle lengths",
                detail=comparison.duration_warning,
                trust_status=TrustStatus.CALCULATED,
            )
        )
    return items


def _snapshot_match(snapshot: SnapshotInput, cycle: CycleInput) -> str | None:
    if not _same_meter(snapshot.meter_reference, cycle.meter_reference):
        return "A comparison is unavailable because the meter does not match the saved forecast."
    if cycle.started_at.date() != snapshot.cycle_started_on or cycle.ended_at.date() != snapshot.cycle_ends_on:
        return "This forecast was saved for a different cycle period."
    if cycle.start_register_kwh != snapshot.cycle_start_register_kwh:
        return "The cycle start register does not match the saved forecast."
    return None


def _view_from_checkpoints(cycle_id: UUID, start, end) -> CycleView:
    actual = end.register_kwh - start.register_kwh
    elapsed = _elapsed_days(start.read_at, end.read_at)
    average = actual / elapsed
    meter = start.meter_reference or ""
    return CycleView(
        id=cycle_id,
        meter_reference=meter,
        start_checkpoint_id=start.id,
        end_checkpoint_id=end.id,
        started_at=start.read_at,
        ended_at=end.read_at,
        start_register_kwh=_q(start.register_kwh),
        end_register_kwh=_q(end.register_kwh),
        actual_kwh=_q(actual),
        duration_days=_q(elapsed),
        average_daily_kwh=_q(average),
        trust_status=TrustStatus.CALCULATED,
        detail=(
            f"Measured use is {_q(actual)} kWh from {start.read_at.date().isoformat()} to {end.read_at.date().isoformat()} "
            f"on meter {meter}. The duration is {_q(elapsed)} days."
        ),
    )


def _view_from_input(cycle: CycleInput) -> CycleView | None:
    if cycle.ended_at <= cycle.started_at or cycle.end_register_kwh < cycle.start_register_kwh:
        return None
    if not _meter_key(cycle.meter_reference):
        return None
    elapsed = _elapsed_days(cycle.started_at, cycle.ended_at)
    if elapsed <= 0:
        return None
    actual = cycle.end_register_kwh - cycle.start_register_kwh
    meter = cycle.meter_reference or ""
    return CycleView(
        id=cycle.id,
        meter_reference=meter,
        start_checkpoint_id=cycle.start_checkpoint_id,
        end_checkpoint_id=cycle.end_checkpoint_id,
        started_at=cycle.started_at,
        ended_at=cycle.ended_at,
        start_register_kwh=_q(cycle.start_register_kwh),
        end_register_kwh=_q(cycle.end_register_kwh),
        actual_kwh=_q(actual),
        duration_days=_q(elapsed),
        average_daily_kwh=_q(actual / elapsed),
        trust_status=TrustStatus.CALCULATED,
        detail=f"Measured use is {_q(actual)} kWh over {_q(elapsed)} days on meter {meter}.",
    )


def _exact_actual(cycle: CycleInput) -> Decimal:
    return cycle.end_register_kwh - cycle.start_register_kwh


def _elapsed(cycle: CycleInput) -> Decimal:
    return _elapsed_days(cycle.started_at, cycle.ended_at)


def _find(readings, checkpoint_id):
    for item in readings:
        if item.id == checkpoint_id:
            return item
    return None


def _overlaps(start: datetime, end: datetime, existing: StoredCycleRef) -> bool:
    return _periods_overlap(start, end, existing.started_at, existing.ended_at)


def _periods_overlap(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < other_end and other_start < end


def _cycle_problem(cycle: CycleInput) -> str | None:
    if cycle.start_checkpoint_id == cycle.end_checkpoint_id:
        return "Each cycle needs two different checkpoints."
    if not _meter_key(cycle.meter_reference):
        return "A comparison needs a recorded meter on both cycles."
    if cycle.ended_at <= cycle.started_at:
        return "Each cycle needs an ending checkpoint later than its start."
    if cycle.end_register_kwh < cycle.start_register_kwh:
        return "A cycle whose register fell was not compared. Consumption was not invented."
    return None


def _same_meter(left: str | None, right: str | None) -> bool:
    return _meter_key(left) == _meter_key(right) and _meter_key(left) != ""


def _rejected_cycle(catalog: TariffCatalog, status: str, detail: str) -> CycleValidateResponse:
    return CycleValidateResponse(
        status=status,  # type: ignore[arg-type]
        cycle=None,
        detail=detail,
        assumptions=_ASSUMPTIONS,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def _blank_compare(catalog: TariffCatalog, detail: str) -> CycleCompareResponse:
    return CycleCompareResponse(
        status="unavailable",
        durations_comparable=False,
        direction="unavailable",
        detail=detail,
        assumptions=_ASSUMPTIONS,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def _blank_forecast(catalog: TariffCatalog, detail: str) -> ForecastComparisonResponse:
    return ForecastComparisonResponse(
        status="unavailable",
        direction="unavailable",
        actual_trust_status=TrustStatus.UNAVAILABLE,
        forecast_trust_status=TrustStatus.ESTIMATED,
        difference_trust_status=TrustStatus.UNAVAILABLE,
        detail=detail,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


def _blank_baseline(catalog: TariffCatalog, detail: str) -> BaselineComparisonResponse:
    return BaselineComparisonResponse(
        status="unavailable",
        direction="unavailable",
        trust_status=TrustStatus.UNAVAILABLE,
        detail=detail,
        limitations=_LIMITS,
        pkr_impact=_pkr(catalog),
    )


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
    reason = (
        "A complete payable file is loaded, but this request has no tariff scope. No rupee saving was calculated."
        if complete
        else _PKR_REASON
    )
    return PkrImpact(value=None, trust_status=TrustStatus.UNAVAILABLE, reason=reason, missing_components=missing, comparable=False)


def _missing_payable(config: TariffConfig) -> list[str]:
    missing: list[str] = []
    if config.synthetic or config.verification_status != "verified":
        missing.append("verified production tariff")
    for item in config.adjustments:
        if item.required_for_payable and item.state != "applicable_verified":
            missing.append(item.label)
    return missing


def _q(value: Decimal) -> str:
    return f"{value.quantize(_KWH, rounding=ROUND_HALF_UP):.3f}"


def _percent(value: Decimal) -> str:
    return f"{value.quantize(_PERCENT, rounding=ROUND_HALF_UP):.2f}"
