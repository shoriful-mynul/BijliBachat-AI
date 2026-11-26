"""Cliff Guard maths. A missing tariff threshold stays missing."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.common import TrustStatus
from app.schemas.meter_api import (
    CliffGuardRequest,
    CliffGuardResponse,
    IntervalView,
    LedgerReading,
    ProjectionView,
    QuantityView,
    ReadingView,
)
from app.schemas.tariff import TariffResolutionQuery
from app.services.meter_validation import _elapsed_days, _meter_key
from app.services.tariff_engine import resolve_tariff
from app.tariffs.loader import TariffCatalog

_KWH = Decimal("0.001")
_HISTORY_MESSAGE = "Not enough reading history for a reliable projection."
_THRESHOLD_MESSAGE = "Threshold needs verification for this tariff configuration."
_NO_THRESHOLD_DETAIL = (
    "The loaded tariff files describe rates and slab bands. "
    "They do not include a verified Cliff Guard threshold, and a slab boundary is not used as one."
)


def evaluate_cliff_guard(catalog: TariffCatalog, request: CliffGuardRequest) -> CliffGuardResponse:
    readings = sorted(
        (item for item in request.readings if _meter_key(item.meter_reference) == _meter_key(request.meter_reference)),
        key=lambda item: item.read_at,
    )
    missing: list[str] = []
    limitations = [
        "These figures come from checkpoints you submitted. They are not a live meter feed.",
        "This API does not keep the checkpoints after the response is sent.",
        _NO_THRESHOLD_DETAIL,
    ]
    warnings: list[str] = []
    latest = readings[-1] if readings else None
    previous = readings[-2] if len(readings) >= 2 else None
    if latest is None:
        missing.append("meter reading")
    consumption, observation = _consumption(previous, latest)
    average = _average(previous, latest, consumption)
    cycle_consumption, cycle_missing = _cycle_consumption(request, latest)
    missing.extend(cycle_missing)
    threshold_status, threshold_value, threshold_source, threshold_missing = _threshold(catalog, request)
    missing.extend(threshold_missing)
    remaining_days = _remaining_days(request)
    remaining_units = _remaining_units(threshold_value, cycle_consumption)
    allowance = _allowance(remaining_units, remaining_days, threshold_value, cycle_consumption)
    projection = _projection(readings, threshold_value, remaining_units, request.as_of)
    if previous is None and latest is not None:
        limitations.append("One checkpoint is not enough to calculate consumption.")
    return CliffGuardResponse(
        latest_reading=_view(latest),
        previous_reading=_view(previous),
        consumption_kwh=consumption,
        observation_period=observation,
        average_daily_kwh=average,
        billing_cycle_consumption_kwh=cycle_consumption,
        billing_cycle_started_on=request.cycle_started_on,
        billing_cycle_ends_on=request.cycle_ends_on,
        threshold_status=threshold_status,
        threshold_kwh=_text(threshold_value) if threshold_value is not None else None,
        threshold_source=threshold_source,
        remaining_kwh=remaining_units,
        remaining_days=remaining_days,
        safe_daily_allowance_kwh=allowance,
        projection=projection,
        last_updated=latest.read_at if latest is not None else None,
        calculated_at=datetime.now(UTC),
        missing_inputs=missing,
        limitations=limitations,
        warnings=warnings,
        intervals=_all_intervals(request.readings),
    )


def safe_daily_allowance(remaining_units: Decimal, remaining_days: Decimal) -> Decimal | None:
    """Formula fixture. A negative allowance is not returned."""
    if remaining_units < 0 or remaining_days <= 0:
        return None
    return (remaining_units / remaining_days).quantize(_KWH, rounding=ROUND_HALF_UP)


def _consumption(previous: LedgerReading | None, latest: LedgerReading | None) -> tuple[QuantityView, str | None]:
    if previous is None or latest is None:
        return _unavailable("Consumption needs two checkpoints from the same meter."), None
    if latest.register_kwh < previous.register_kwh:
        return (
            _unavailable(
                "Consumption was not calculated because the register decreased. "
                "The check does not choose a reason."
            ),
            None,
        )
    elapsed = _elapsed_days(previous.read_at, latest.read_at)
    if elapsed <= 0:
        return _unavailable("The two checkpoints have no time between them, so consumption was not averaged."), None
    used = (latest.register_kwh - previous.register_kwh).quantize(_KWH, rounding=ROUND_HALF_UP)
    period = f"{previous.read_at.date().isoformat()} to {latest.read_at.date().isoformat()}"
    return (
        QuantityView(
            value=f"{used:.3f}",
            trust_status=TrustStatus.CALCULATED,
            detail=f"Calculated from the two latest checkpoints for this meter, {period}.",
        ),
        period,
    )


def _average(previous: LedgerReading | None, latest: LedgerReading | None, consumption: QuantityView) -> QuantityView:
    if previous is None or latest is None or consumption.value is None:
        return _unavailable("Average daily use needs a calculated consumption and a period longer than zero.")
    elapsed = _elapsed_days(previous.read_at, latest.read_at)
    if elapsed <= 0:
        return _unavailable("Average daily use was not calculated because no time passed between the checkpoints.")
    average = (Decimal(consumption.value) / elapsed).quantize(_KWH, rounding=ROUND_HALF_UP)
    return QuantityView(
        value=f"{average:.3f}",
        trust_status=TrustStatus.CALCULATED,
        detail=(
            f"Calculated as consumption divided by {elapsed.quantize(_KWH, rounding=ROUND_HALF_UP)} days "
            "between the two latest checkpoints."
        ),
    )


def _cycle_consumption(request: CliffGuardRequest, latest: LedgerReading | None) -> tuple[QuantityView, list[str]]:
    if request.cycle_started_on is None or request.cycle_ends_on is None or request.cycle_start_register_kwh is None:
        return (
            _unavailable("Billing-cycle consumption needs an explicit start reading and cycle dates."),
            ["billing-cycle start reading"] if latest is not None else [],
        )
    if request.cycle_ends_on < request.cycle_started_on:
        return _unavailable("The billing-cycle end is earlier than its start."), []
    if latest is None:
        return _unavailable("Billing-cycle consumption needs a checkpoint inside the cycle."), ["meter reading"]
    if latest.read_at.date() < request.cycle_started_on or latest.read_at.date() > request.cycle_ends_on:
        return _unavailable("The latest checkpoint is outside the stated billing cycle."), []
    if latest.register_kwh < request.cycle_start_register_kwh:
        return _unavailable("The latest register is below the stated cycle-start register."), []
    used = (latest.register_kwh - request.cycle_start_register_kwh).quantize(_KWH, rounding=ROUND_HALF_UP)
    return (
        QuantityView(
            value=f"{used:.3f}",
            trust_status=TrustStatus.CALCULATED,
            detail=(
                "Calculated from the cycle-start register you supplied and the latest checkpoint. "
                "An earlier checkpoint was not treated as the cycle start."
            ),
        ),
        [],
    )


def _threshold(catalog: TariffCatalog, request: CliffGuardRequest) -> tuple[str, Decimal | None, str | None, list[str]]:
    if not request.provider_code or not request.consumer_category or not request.tariff_type or not request.billing_date:
        return (
            "unavailable",
            None,
            None,
            ["tariff scope"],
        )
    query = TariffResolutionQuery(
        provider_code=request.provider_code,
        consumer_category=request.consumer_category,
        tariff_type=request.tariff_type,
        eligibility=request.eligibility,
        billing_date=request.billing_date,
    )
    resolved = resolve_tariff(catalog, query)
    if resolved.configuration is None:
        return ("unavailable", None, None, [])
    # No loaded file defines cliff_threshold_kwh. Slab edges stay rate bands.
    return (
        "needs_verification",
        None,
        f"{resolved.configuration.config_id} {resolved.configuration.version}",
        [],
    )


def _remaining_days(request: CliffGuardRequest) -> QuantityView:
    if request.cycle_ends_on is None:
        return _unavailable("Days remaining need a billing-cycle end date.")
    days = (request.cycle_ends_on - request.as_of.date()).days
    if days <= 0:
        return _unavailable("The billing-cycle end date is today or already past, so remaining days are not used.")
    return QuantityView(
        value=str(days),
        trust_status=TrustStatus.CALCULATED,
        detail="Calculated as the number of midnights from the stated moment until the cycle end date.",
    )


def _remaining_units(threshold: Decimal | None, cycle: QuantityView) -> QuantityView:
    if threshold is None:
        return _unavailable(_THRESHOLD_MESSAGE)
    if cycle.value is None:
        return _unavailable("Remaining units need billing-cycle consumption and a verified threshold.")
    remaining = threshold - Decimal(cycle.value)
    if remaining < 0:
        return QuantityView(
            value=None,
            trust_status=TrustStatus.CALCULATED,
            detail="The stated cycle consumption is already past the verified threshold.",
        )
    return QuantityView(
        value=f"{remaining.quantize(_KWH, rounding=ROUND_HALF_UP):.3f}",
        trust_status=TrustStatus.CALCULATED,
        detail="Calculated as the verified threshold minus billing-cycle consumption.",
    )


def _allowance(
    remaining: QuantityView,
    days: QuantityView,
    threshold: Decimal | None,
    cycle: QuantityView,
) -> QuantityView:
    if threshold is None:
        return _unavailable(_THRESHOLD_MESSAGE)
    if cycle.value is not None and Decimal(cycle.value) > threshold:
        return QuantityView(
            value=None,
            trust_status=TrustStatus.UNAVAILABLE,
            detail="The cycle is already past the verified threshold, so no daily allowance is recommended.",
        )
    if remaining.value is None or days.value is None:
        return _unavailable("A daily allowance needs remaining units and remaining days.")
    amount = safe_daily_allowance(Decimal(remaining.value), Decimal(days.value))
    if amount is None:
        return _unavailable("A daily allowance was not calculated.")
    return QuantityView(
        value=f"{amount:.3f}",
        trust_status=TrustStatus.CALCULATED,
        detail="Calculated as remaining units divided by remaining days.",
    )


def _projection(
    readings: list[LedgerReading],
    threshold: Decimal | None,
    remaining: QuantityView,
    as_of: datetime,
) -> ProjectionView:
    if len(readings) < 3 or _elapsed_days(readings[0].read_at, readings[-1].read_at) < 2:
        return ProjectionView(
            status="unavailable",
            message=_HISTORY_MESSAGE,
            trust_status=TrustStatus.UNAVAILABLE,
            assumptions=[],
        )
    if threshold is None or remaining.value is None:
        return ProjectionView(
            status="unavailable",
            message=_THRESHOLD_MESSAGE,
            trust_status=TrustStatus.UNAVAILABLE,
            assumptions=["The projection uses only a verified threshold and the observed daily pace."],
        )
    elapsed = _elapsed_days(readings[0].read_at, readings[-1].read_at)
    used = readings[-1].register_kwh - readings[0].register_kwh
    if elapsed <= 0 or used <= 0:
        return ProjectionView(
            status="unavailable",
            message=_HISTORY_MESSAGE,
            trust_status=TrustStatus.UNAVAILABLE,
            assumptions=[],
        )
    pace = used / elapsed
    days = (Decimal(remaining.value) / pace).quantize(_KWH, rounding=ROUND_HALF_UP)
    whole_days = int(days.to_integral_value(rounding=ROUND_HALF_UP))
    period = f"{readings[0].read_at.date().isoformat()} to {readings[-1].read_at.date().isoformat()}"
    return ProjectionView(
        status="estimated",
        message="The projected date assumes the observed daily pace continues.",
        projected_date=as_of.date() + timedelta(days=whole_days),
        trust_status=TrustStatus.ESTIMATED,
        observation_period=period,
        assumptions=[
            "The pace is the change from the earliest to the latest checkpoint divided by the days between them.",
            "The projection is an estimate, not a verified bill.",
        ],
    )


def _all_intervals(readings: list[LedgerReading]) -> list[IntervalView]:
    groups: dict[str, list[LedgerReading]] = {}
    for item in readings:
        groups.setdefault(_meter_key(item.meter_reference), []).append(item)
    rows: list[IntervalView] = []
    for group in groups.values():
        rows.extend(_intervals(sorted(group, key=lambda item: item.read_at)))
    return rows


def _intervals(readings: list[LedgerReading]) -> list[IntervalView]:
    rows: list[IntervalView] = []
    for previous, latest in zip(readings, readings[1:], strict=False):
        quantity, _period = _consumption(previous, latest)
        rows.append(
            IntervalView(
                reading_id=latest.id,
                consumed_kwh=quantity.value,
                trust_status=quantity.trust_status,
                detail=quantity.detail,
            )
        )
    return rows


def _view(reading: LedgerReading | None) -> ReadingView | None:
    if reading is None:
        return None
    return ReadingView(
        id=reading.id,
        register_kwh=f"{reading.register_kwh:.3f}",
        read_at=reading.read_at,
        meter_reference=reading.meter_reference,
        trust_status=reading.trust_status,
    )


def _unavailable(detail: str) -> QuantityView:
    return QuantityView(value=None, trust_status=TrustStatus.UNAVAILABLE, detail=detail)


def _text(value: Decimal) -> str:
    return f"{value.quantize(_KWH, rounding=ROUND_HALF_UP):.3f}"


def empty_cliff_request(as_of: datetime | None = None) -> CliffGuardRequest:
    return CliffGuardRequest(as_of=as_of or datetime.now(UTC))
