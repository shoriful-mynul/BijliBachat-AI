"""Deterministic tariff arithmetic.

Every rate comes from the configuration passed in. A missing rate, input, or
file becomes an unavailable result. This module does not borrow another
company's schedule or treat a missing component as zero.
"""

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.common import TrustStatus
from app.schemas.tariff import (
    AdjustmentView,
    AvailabilityView,
    CalculationComponent,
    CalculationInputs,
    SlabLine,
    SlabView,
    TariffCalculationRequest,
    TariffCalculationResponse,
    TariffCatalogResponse,
    TariffMetadata,
    TariffResolutionQuery,
    TariffResolutionResponse,
    TariffSourceView,
)
from app.tariffs.loader import TariffCatalog
from app.tariffs.models import Adjustment, Slab, TariffConfig, TariffConfigError

MONEY = Decimal("0.01")
HALF = Decimal("0.5")
HUNDRED = Decimal("100")


def list_configurations(catalog: TariffCatalog) -> TariffCatalogResponse:
    return TariffCatalogResponse(
        configurations=[configuration_metadata(config) for config in catalog.configs],
        unavailable=[_availability_view(entry) for entry in catalog.availability],
    )


def resolve_tariff(
    catalog: TariffCatalog,
    query: TariffResolutionQuery,
) -> TariffResolutionResponse:
    refusal = _scope_refusal(query.tariff_type, query.eligibility)
    if refusal is not None:
        code, reason, missing = refusal
        return _resolution(
            query,
            reason_code=code,
            reason=reason,
            missing_inputs=missing,
            limitations=_notes_for(catalog, query)[1],
        )
    matches = _matching_configs(catalog, query)
    if len(matches) > 1:
        names = ", ".join(config.config_id for config in matches)
        return _resolution(
            query,
            reason_code="ambiguous_configuration",
            reason=(
                f"More than one tariff configuration matches this request ({names}). "
                "None of them was used."
            ),
        )
    if len(matches) == 1:
        config = matches[0]
        if config.verification_status != "verified":
            return _resolution(
                query,
                reason_code="unverified_configuration",
                reason=(
                    "A configuration exists for this request, and it is not verified. "
                    "It was not used for a calculation."
                ),
                configuration=configuration_metadata(config),
                limitations=list(config.source.limitations),
            )
        return _resolution(
            query,
            outcome="matched",
            reason_code="matched",
            reason="One verified configuration covers this distribution company, category, and billing date.",
            configuration=configuration_metadata(config),
            limitations=list(config.source.limitations),
        )
    code, reason, limitations = _no_match_explanation(catalog, query)
    return _resolution(query, reason_code=code, reason=reason, limitations=limitations)


def calculate_tariff(
    catalog: TariffCatalog,
    request: TariffCalculationRequest,
) -> TariffCalculationResponse:
    refusal = _scope_refusal(request.tariff_type, request.eligibility)
    if refusal is not None:
        code, reason, missing = refusal
        return _unavailable_calculation(request, reason_code=code, reason=reason, missing_inputs=missing)
    matches = _matching_configs(catalog, request)
    if len(matches) > 1:
        names = ", ".join(config.config_id for config in matches)
        return _unavailable_calculation(
            request,
            reason_code="ambiguous_configuration",
            reason=(
                f"More than one tariff configuration matches this request ({names}). "
                "No amount was calculated."
            ),
        )
    if not matches:
        code, reason, limitations = _no_match_explanation(catalog, request)
        return _unavailable_calculation(
            request,
            reason_code=code,
            reason=reason,
            limitations=limitations,
        )
    config = matches[0]
    if config.verification_status != "verified":
        return _unavailable_calculation(
            request,
            reason_code="unverified_configuration",
            reason=(
                "The matching configuration is not verified. No energy, fixed, tax, "
                "or payable amount was calculated from it."
            ),
            config=config,
        )
    inconsistent = _inconsistent_tou(config, request)
    if inconsistent is not None:
        return _unavailable_calculation(
            request,
            reason_code="inconsistent_inputs",
            reason=inconsistent,
            config=config,
        )
    return _calculate_verified(config, request)


def configuration_metadata(config: TariffConfig) -> TariffMetadata:
    return TariffMetadata(
        config_id=config.config_id,
        version=config.version,
        provider_code=config.provider_code,
        consumer_category=config.consumer_category,
        tariff_type=config.tariff_type,
        eligibility=config.eligibility,
        schedule_name=config.schedule_name,
        billing_frequency=config.billing_frequency,
        effective_from=config.effective_from,
        effective_to=config.effective_to,
        slab_method=config.slab_method,
        verification_status=config.verification_status,
        synthetic=config.synthetic,
        payable_total_available=_payable_file(config),
        slabs=[
            SlabView(
                lower_exclusive_kwh=slab.lower_exclusive_kwh,
                upper_inclusive_kwh=slab.upper_inclusive_kwh,
                rate_per_kwh=slab.rate_per_kwh,
                fixed_charge_per_kw=slab.fixed_charge_per_kw,
            )
            for slab in config.slabs
        ],
        fixed_charge_state=config.fixed_charge.state,
        fixed_charge_basis=config.fixed_charge.basis,
        minimum_charge_state=config.minimum_charge.state,
        adjustments=[
            AdjustmentView(
                code=item.code,
                label=item.label,
                state=item.state,
                required_for_payable=item.required_for_payable,
                reason=item.reason,
            )
            for item in config.adjustments
        ],
        source=_source_view(config),
        limitations=list(config.source.limitations),
    )


def _calculate_verified(
    config: TariffConfig,
    request: TariffCalculationRequest,
) -> TariffCalculationResponse:
    missing: list[str] = []
    assumptions: list[str] = []
    energy, marginal = _energy(config, request, missing)
    fixed = _fixed_charge(config, request, marginal, missing, assumptions)
    minimum = _minimum_charge(config, request, missing)
    components = [energy, fixed, minimum]
    by_code = {item.code: item for item in components}
    for adjustment in config.adjustments:
        built = _adjustment(adjustment, by_code)
        components.append(built)
        by_code[built.code] = built

    blocking = [item.code for item in components if item.blocks and item.amount is None]
    produced_money = any(item.amount is not None for item in components)
    if produced_money and config.rounding.source_status == "engine_convention":
        assumptions.append(config.rounding.note)
    payable = (
        not missing
        and not blocking
        and energy.amount is not None
        and (config.fixed_charge.state != "applicable_verified" or fixed.amount is not None)
        and not (minimum.code == "minimum_charge" and minimum.blocks and minimum.amount is None)
    )
    public = [_public_component(item) for item in components]
    if payable:
        total = quantize_money(
            sum((item.amount for item in components if item.amount is not None), start=Decimal("0"))
        )
        return _response(
            request,
            outcome="calculated",
            trust_status=TrustStatus.CALCULATED,
            reason_code="complete",
            reason="Every required component in this configuration was calculated.",
            config=config,
            inputs=_inputs(request),
            components=public,
            final_amount=total,
            assumptions=assumptions,
        )
    if missing:
        code = "missing_input"
        reason = "A required input is missing. No payable total was calculated, and no missing rate was treated as zero."
    elif energy.amount is None or (
        config.fixed_charge.state == "applicable_verified" and fixed.amount is None and not missing
    ):
        code = "consumption_not_covered"
        reason = (
            "The configuration has no slab for this consumption. "
            "The household was not moved into another category."
        )
    else:
        code = "incomplete_components"
        reason = (
            "One or more required bill components are not in the verified configuration. "
            "The amounts that were calculated are not a payable total."
        )
    return _response(
        request,
        outcome="unavailable",
        trust_status=TrustStatus.UNAVAILABLE,
        reason_code=code,
        reason=reason,
        config=config,
        inputs=_inputs(request),
        missing_inputs=missing,
        blocking_components=blocking,
        components=public,
        assumptions=assumptions,
    )


class _Built:
    def __init__(
        self,
        code: str,
        label: str,
        state: str,
        detail: str,
        *,
        amount: Decimal | None = None,
        lines: list[SlabLine] | None = None,
        blocks: bool = False,
    ) -> None:
        if amount is not None:
            amount = quantize_money(amount)
        self.code = code
        self.label = label
        self.state = state
        self.detail = detail
        self.amount = amount
        self.lines = lines or []
        self.blocks = blocks


def _energy(
    config: TariffConfig,
    request: TariffCalculationRequest,
    missing: list[str],
) -> tuple[_Built, Slab | None]:
    if config.slab_method == "time_of_use":
        return _tou_energy(config, request, missing), None
    if request.consumption_kwh == 0:
        return (
            _Built(
                "energy_charge",
                "Energy charge",
                "applicable_verified",
                "Consumption is 0 kWh, so the energy charge is 0.00.",
                amount=Decimal("0"),
            ),
            None,
        )
    lines = _consumption_lines(config, request.consumption_kwh)
    if lines is None:
        return (
            _Built(
                "energy_charge",
                "Energy charge",
                "unavailable",
                "No slab in this confirmed category covers this consumption. It was not reclassified.",
                blocks=True,
            ),
            None,
        )
    exact = sum((line[2] for line in lines), start=Decimal("0"))
    public_lines = [
        SlabLine(label=label, units=units, rate_per_kwh=slab.rate_per_kwh, exact_amount=product)
        for slab, units, product, label in lines
    ]
    return (
        _Built(
            "energy_charge",
            "Energy charge",
            "applicable_verified",
            _energy_detail(config.slab_method, lines),
            amount=exact,
            lines=public_lines,
        ),
        lines[-1][0],
    )


def _tou_energy(
    config: TariffConfig,
    request: TariffCalculationRequest,
    missing: list[str],
) -> _Built:
    rates = config.time_of_use
    if rates is None:
        raise TariffConfigError("A time-of-use configuration is missing its rates.")
    if request.peak_kwh is None:
        missing.append("peak_kwh")
    if request.off_peak_kwh is None:
        missing.append("off_peak_kwh")
    if request.peak_kwh is None or request.off_peak_kwh is None:
        return _Built(
            "energy_charge",
            "Energy charge",
            "unavailable",
            "Peak and off-peak units are both required. A missing part was not treated as zero.",
            blocks=True,
        )
    peak = request.peak_kwh * rates.peak_rate_per_kwh
    off_peak = request.off_peak_kwh * rates.off_peak_rate_per_kwh
    lines = [
        SlabLine(
            label="Peak units",
            units=request.peak_kwh,
            rate_per_kwh=rates.peak_rate_per_kwh,
            exact_amount=peak,
        ),
        SlabLine(
            label="Off-peak units",
            units=request.off_peak_kwh,
            rate_per_kwh=rates.off_peak_rate_per_kwh,
            exact_amount=off_peak,
        ),
    ]
    return _Built(
        "energy_charge",
        "Energy charge",
        "applicable_verified",
        (
            f"{plain(request.peak_kwh)} kWh × {plain(rates.peak_rate_per_kwh)} peak, plus "
            f"{plain(request.off_peak_kwh)} kWh × {plain(rates.off_peak_rate_per_kwh)} off-peak."
        ),
        amount=peak + off_peak,
        lines=lines,
    )


def _fixed_charge(
    config: TariffConfig,
    request: TariffCalculationRequest,
    marginal: Slab | None,
    missing: list[str],
    assumptions: list[str],
) -> _Built:
    policy = config.fixed_charge
    if policy.state == "not_applicable":
        return _Built(
            "fixed_charge",
            "Fixed charge",
            "not_applicable",
            policy.reason,
        )
    if policy.state != "applicable_verified":
        return _Built(
            "fixed_charge",
            "Fixed charge",
            policy.state,
            policy.reason,
            blocks=True,
        )
    if policy.basis == "per_kw_of_sanctioned_load":
        if request.consumption_kwh == 0 or marginal is None or marginal.fixed_charge_per_kw is None:
            return _Built(
                "fixed_charge",
                "Fixed charge",
                "unavailable",
                "No slab covers this consumption, so the fixed charge for that slab cannot be selected.",
                blocks=True,
            )
        if request.sanctioned_load_kw is None:
            missing.append("sanctioned_load_kw")
            return _Built(
                "fixed_charge",
                "Fixed charge",
                "unavailable",
                "Sanctioned load in kW is required. It was not assumed.",
                blocks=True,
            )
        exact = request.sanctioned_load_kw * marginal.fixed_charge_per_kw
        return _Built(
            "fixed_charge",
            "Fixed charge",
            "applicable_verified",
            (
                f"{plain(request.sanctioned_load_kw)} kW × {plain(marginal.fixed_charge_per_kw)} "
                "per kW for the selected slab."
            ),
            amount=exact,
        )
    if request.sanctioned_load_kw is None:
        missing.append("sanctioned_load_kw")
        return _Built(
            "fixed_charge",
            "Fixed charge",
            "unavailable",
            "Sanctioned load in kW is required. It was not assumed.",
            blocks=True,
        )
    if policy.rate_per_kw is None:
        raise TariffConfigError("A time-of-use fixed charge is missing its rate.")
    half_load = request.sanctioned_load_kw * HALF
    if request.maximum_demand_kw is None:
        if policy.mdi_optional_through is not None and request.billing_date <= policy.mdi_optional_through:
            assumptions.append(
                "MDI was not supplied. This configuration says that, through "
                f"{policy.mdi_optional_through.isoformat()}, fixed charges use 50 percent of sanctioned load."
            )
            return _Built(
                "fixed_charge",
                "Fixed charge",
                "applicable_verified",
                (
                    f"{plain(half_load)} kW, half the sanctioned load, × {plain(policy.rate_per_kw)} per kW."
                ),
                amount=half_load * policy.rate_per_kw,
            )
        missing.append("maximum_demand_kw")
        return _Built(
            "fixed_charge",
            "Fixed charge",
            "unavailable",
            "MDI is required for this billing date. Half the sanctioned load was not substituted.",
            blocks=True,
        )
    billable = max(half_load, request.maximum_demand_kw)
    return _Built(
        "fixed_charge",
        "Fixed charge",
        "applicable_verified",
        (
            f"{plain(billable)} kW, the higher of half the sanctioned load and MDI, "
            f"× {plain(policy.rate_per_kw)} per kW."
        ),
        amount=billable * policy.rate_per_kw,
    )


def _minimum_charge(
    config: TariffConfig,
    request: TariffCalculationRequest,
    missing: list[str],
) -> _Built:
    policy = config.minimum_charge
    if policy.state == "not_applicable":
        return _Built("minimum_charge", "Minimum charge", "not_applicable", policy.reason)
    if policy.state != "applicable_verified":
        return _Built(
            "minimum_charge",
            "Minimum charge",
            policy.state,
            policy.reason,
            blocks=True,
        )
    if request.consumption_kwh != 0:
        return _Built(
            "minimum_charge",
            "Minimum charge",
            "not_applicable",
            "The minimum charge in this file applies only when consumption is zero.",
        )
    if request.phase is None:
        missing.append("phase")
        return _Built(
            "minimum_charge",
            "Minimum charge",
            "unavailable",
            "The phase is required to select the zero-consumption minimum charge.",
            blocks=True,
        )
    amount = policy.single_phase_amount if request.phase == "single" else policy.three_phase_amount
    if amount is None:
        raise TariffConfigError("A minimum charge is missing a phase amount.")
    return _Built(
        "minimum_charge",
        "Minimum charge",
        "applicable_verified",
        f"Zero consumption, {request.phase}-phase minimum charge of {plain(amount)}.",
        amount=amount,
    )


def _adjustment(adjustment: Adjustment, by_code: dict[str, _Built]) -> _Built:
    if adjustment.state != "applicable_verified":
        blocks = adjustment.required_for_payable
        return _Built(
            adjustment.code,
            adjustment.label,
            adjustment.state,
            adjustment.reason,
            blocks=blocks,
        )
    if adjustment.basis == "flat_amount":
        if adjustment.amount is None:
            raise TariffConfigError("A flat adjustment is missing its amount.")
        return _Built(
            adjustment.code,
            adjustment.label,
            "applicable_verified",
            adjustment.reason,
            amount=adjustment.amount,
        )
    if adjustment.percent is None:
        raise TariffConfigError("A percent adjustment is missing its percent.")
    bases: list[Decimal] = []
    for code in adjustment.applies_to:
        base = by_code.get(code)
        if base is None or base.state == "not_applicable":
            continue
        if base.amount is None:
            return _Built(
                adjustment.code,
                adjustment.label,
                "unavailable",
                f"{adjustment.label} was not calculated because {code} is unavailable. It was not treated as zero.",
                blocks=adjustment.required_for_payable,
            )
        bases.append(base.amount)
    if not bases:
        return _Built(
            adjustment.code,
            adjustment.label,
            "unavailable",
            f"{adjustment.label} has no calculated base component to apply to.",
            blocks=adjustment.required_for_payable,
        )
    exact = sum(bases, start=Decimal("0")) * adjustment.percent / HUNDRED
    return _Built(
        adjustment.code,
        adjustment.label,
        "applicable_verified",
        (
            f"{plain(adjustment.percent)} percent of {', '.join(adjustment.applies_to)} "
            "after those components were rounded."
        ),
        amount=exact,
    )


def _consumption_lines(
    config: TariffConfig,
    units: Decimal,
) -> list[tuple[Slab, Decimal, Decimal, str]] | None:
    if config.slab_method == "single_slab":
        return _single_lines(config, units)
    if config.slab_method == "progressive_marginal":
        return _progressive_lines(config, units)
    if config.slab_method == "one_previous_slab":
        return _one_previous_lines(config, units)
    return None


def _single_lines(
    config: TariffConfig,
    units: Decimal,
) -> list[tuple[Slab, Decimal, Decimal, str]] | None:
    matches = [slab for slab in config.slabs if _contains(slab, units)]
    if len(matches) != 1:
        return None
    slab = matches[0]
    return [(slab, units, units * slab.rate_per_kwh, "All consumed units at the selected slab rate")]


def _progressive_lines(
    config: TariffConfig,
    units: Decimal,
) -> list[tuple[Slab, Decimal, Decimal, str]] | None:
    lines: list[tuple[Slab, Decimal, Decimal, str]] = []
    for slab in config.slabs:
        if units <= slab.lower_exclusive_kwh:
            break
        upper = units if slab.upper_inclusive_kwh is None else min(slab.upper_inclusive_kwh, units)
        band_units = upper - slab.lower_exclusive_kwh
        if band_units <= 0:
            continue
        label = f"Units above {plain(slab.lower_exclusive_kwh)} kWh and up to {plain(upper)} kWh"
        lines.append((slab, band_units, band_units * slab.rate_per_kwh, label))
        if slab.upper_inclusive_kwh is None or units <= slab.upper_inclusive_kwh:
            return lines
    return None


def _one_previous_lines(
    config: TariffConfig,
    units: Decimal,
) -> list[tuple[Slab, Decimal, Decimal, str]] | None:
    matches = [slab for slab in config.slabs if _contains(slab, units)]
    if len(matches) != 1:
        return None
    current = matches[0]
    index = config.slabs.index(current)
    if index == 0:
        return [(current, units, units * current.rate_per_kwh, "All consumed units at the first slab rate")]
    previous = config.slabs[index - 1]
    split = previous.upper_inclusive_kwh
    if split is None or split <= 0 or split >= units:
        return None
    return [
        (
            previous,
            split,
            split * previous.rate_per_kwh,
            "Units through the previous slab, at that slab's rate",
        ),
        (
            current,
            units - split,
            (units - split) * current.rate_per_kwh,
            "Units above the previous slab, at the current slab's rate",
        ),
    ]


def _contains(slab: Slab, units: Decimal) -> bool:
    if units <= slab.lower_exclusive_kwh:
        return False
    if slab.upper_inclusive_kwh is not None and units > slab.upper_inclusive_kwh:
        return False
    return True


def _energy_detail(method: str, lines: list[tuple[Slab, Decimal, Decimal, str]]) -> str:
    names = {
        "single_slab": "single applicable slab",
        "progressive_marginal": "progressive marginal slabs",
        "one_previous_slab": "one previous slab",
    }
    parts = [
        f"{plain(units)} kWh × {plain(slab.rate_per_kwh)}"
        for slab, units, _product, _label in lines
    ]
    return f"{names.get(method, method)}: " + " + ".join(parts) + "."


def _scope_refusal(tariff_type: str, eligibility: str | None) -> tuple[str, str, list[str]] | None:
    if tariff_type == "tou" and eligibility is not None:
        return (
            "inconsistent_inputs",
            "Time-of-use resolution does not take a lifeline, protected, or unprotected label.",
            [],
        )
    if tariff_type == "non_tou" and eligibility is None:
        return (
            "missing_input",
            "Confirm the consumer category. Current monthly consumption is not used to classify it.",
            ["eligibility"],
        )
    return None


def _inconsistent_tou(config: TariffConfig, request: TariffCalculationRequest) -> str | None:
    if config.slab_method != "time_of_use":
        if request.peak_kwh is not None or request.off_peak_kwh is not None:
            return "Peak and off-peak units do not apply to this configuration."
        return None
    if request.peak_kwh is None or request.off_peak_kwh is None:
        return None
    if request.peak_kwh + request.off_peak_kwh != request.consumption_kwh:
        return "Peak units plus off-peak units must equal total consumption."
    return None


def _matching_configs(catalog: TariffCatalog, query: TariffResolutionQuery | TariffCalculationRequest) -> list[TariffConfig]:
    return [
        config
        for config in catalog.configs
        if config.provider_code.casefold() == query.provider_code.casefold()
        and config.consumer_category.casefold() == query.consumer_category.casefold()
        and config.tariff_type == query.tariff_type
        and config.eligibility == query.eligibility
        and config.covers(query.billing_date)
    ]


def _no_match_explanation(
    catalog: TariffCatalog,
    query: TariffResolutionQuery | TariffCalculationRequest,
) -> tuple[str, str, list[str]]:
    same_scope = [
        config
        for config in catalog.configs
        if config.provider_code.casefold() == query.provider_code.casefold()
        and config.consumer_category.casefold() == query.consumer_category.casefold()
        and config.tariff_type == query.tariff_type
        and config.eligibility == query.eligibility
    ]
    if same_scope:
        windows = [
            (
                f"{config.config_id} is effective from {config.effective_from.isoformat()} "
                f"to {config.effective_to.isoformat() if config.effective_to else 'an open end'}."
            )
            for config in same_scope
        ]
        return (
            "no_applicable_configuration",
            "No configuration is effective on this billing date. An expired or not-yet-effective file was not used.",
            windows,
        )
    known_provider = any(
        item.provider_code.casefold() == query.provider_code.casefold()
        for item in (*catalog.configs, *catalog.availability)
    )
    notes, limitations = _notes_for(catalog, query)
    if not known_provider:
        return (
            "unsupported_provider",
            "No tariff configuration is loaded for this distribution company. Another company's schedule was not used.",
            ["No rates were substituted from a different provider."],
        )
    known_category = any(
        config.consumer_category.casefold() == query.consumer_category.casefold()
        for config in catalog.configs
        if config.provider_code.casefold() == query.provider_code.casefold()
    ) or any(
        entry.consumer_category is None
        or entry.consumer_category.casefold() == query.consumer_category.casefold()
        for entry in catalog.availability
        if entry.provider_code.casefold() == query.provider_code.casefold()
    )
    if not known_category:
        return (
            "unknown_category",
            "No tariff configuration is loaded for this consumer category. A residential schedule was not substituted.",
            limitations or ["The category was not mapped onto another category."],
        )
    if any(entry.status == "needs_verification" for entry in notes):
        reason = " ".join(entry.reason for entry in notes) or (
            "The category needs verification. It was not inferred from consumption."
        )
        return ("needs_verification", reason, limitations or [reason])
    reason = " ".join(entry.reason for entry in notes) or (
        "No configuration covers this distribution company, category, and billing date. "
        "An older or different configuration was not used."
    )
    return ("no_applicable_configuration", reason, limitations or [reason])


def _notes_for(
    catalog: TariffCatalog,
    query: TariffResolutionQuery | TariffCalculationRequest,
) -> tuple[list, list[str]]:
    notes = []
    for entry in catalog.availability:
        if entry.provider_code.casefold() != query.provider_code.casefold():
            continue
        if (
            entry.consumer_category is not None
            and entry.consumer_category.casefold() != query.consumer_category.casefold()
        ):
            continue
        if entry.tariff_type is not None and entry.tariff_type != query.tariff_type:
            continue
        if entry.eligibility is not None and entry.eligibility != query.eligibility:
            continue
        notes.append(entry)
    specific = [
        entry
        for entry in notes
        if entry.consumer_category is not None or entry.tariff_type is not None or entry.eligibility is not None
    ]
    notes = specific or notes
    limitations: list[str] = []
    for entry in notes:
        limitations.append(entry.reason)
        limitations.extend(entry.limitations)
    return notes, limitations


def _payable_file(config: TariffConfig) -> bool:
    if config.verification_status != "verified":
        return False
    if config.fixed_charge.state in {"unavailable", "needs_verification"}:
        return False
    if config.minimum_charge.state in {"unavailable", "needs_verification"}:
        return False
    return all(
        item.state == "applicable_verified"
        for item in config.adjustments
        if item.required_for_payable
    )


def _public_component(item: _Built) -> CalculationComponent:
    return CalculationComponent(
        code=item.code,
        label=item.label,
        state=item.state,  # type: ignore[arg-type]
        amount=item.amount,
        trust_status=TrustStatus.CALCULATED if item.amount is not None else TrustStatus.UNAVAILABLE,
        detail=item.detail,
        lines=item.lines,
    )


def _inputs(request: TariffCalculationRequest) -> CalculationInputs:
    return CalculationInputs(
        consumption_kwh=request.consumption_kwh,
        peak_kwh=request.peak_kwh,
        off_peak_kwh=request.off_peak_kwh,
        sanctioned_load_kw=request.sanctioned_load_kw,
        maximum_demand_kw=request.maximum_demand_kw,
        phase=request.phase,
    )


def _source_view(config: TariffConfig) -> TariffSourceView:
    source = config.source
    return TariffSourceView(
        issuing_authority=source.issuing_authority,
        document_title=source.document_title,
        source_url=source.source_url,
        notification_date=source.notification_date,
        retrieval_date=source.retrieval_date,
        reference=source.reference,
        verification_status=source.verification_status,
    )


def _availability_view(entry) -> AvailabilityView:
    return AvailabilityView(
        provider_code=entry.provider_code,
        consumer_category=entry.consumer_category,
        tariff_type=entry.tariff_type,
        eligibility=entry.eligibility,
        status=entry.status,
        reason=entry.reason,
        source_url=entry.source_url,
        retrieval_date=entry.retrieval_date,
        limitations=list(entry.limitations),
    )


def _resolution(
    query: TariffResolutionQuery,
    *,
    reason_code: str,
    reason: str,
    outcome: str = "unavailable",
    configuration: TariffMetadata | None = None,
    missing_inputs: list[str] | None = None,
    limitations: list[str] | None = None,
) -> TariffResolutionResponse:
    return TariffResolutionResponse(
        outcome=outcome,  # type: ignore[arg-type]
        reason_code=reason_code,
        reason=reason,
        provider_code=query.provider_code,
        consumer_category=query.consumer_category,
        tariff_type=query.tariff_type,
        eligibility=query.eligibility,
        billing_date=query.billing_date,
        configuration=configuration,
        missing_inputs=missing_inputs or [],
        limitations=limitations or [],
    )


def _unavailable_calculation(
    request: TariffCalculationRequest,
    *,
    reason_code: str,
    reason: str,
    config: TariffConfig | None = None,
    missing_inputs: list[str] | None = None,
    limitations: list[str] | None = None,
) -> TariffCalculationResponse:
    return _response(
        request,
        outcome="unavailable",
        trust_status=TrustStatus.UNAVAILABLE,
        reason_code=reason_code,
        reason=reason,
        config=config,
        inputs=_inputs(request),
        missing_inputs=missing_inputs or [],
        limitations=limitations if limitations is not None else (list(config.source.limitations) if config else []),
    )


def _response(
    request: TariffCalculationRequest,
    *,
    outcome: str,
    trust_status: TrustStatus,
    reason_code: str,
    reason: str,
    inputs: CalculationInputs,
    config: TariffConfig | None = None,
    missing_inputs: list[str] | None = None,
    blocking_components: list[str] | None = None,
    components: list[CalculationComponent] | None = None,
    final_amount: Decimal | None = None,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> TariffCalculationResponse:
    return TariffCalculationResponse(
        outcome=outcome,  # type: ignore[arg-type]
        trust_status=trust_status,
        reason_code=reason_code,
        reason=reason,
        provider_code=request.provider_code,
        consumer_category=request.consumer_category,
        tariff_type=request.tariff_type,
        eligibility=request.eligibility,
        billing_date=request.billing_date,
        config_id=config.config_id if config else None,
        config_version=config.version if config else None,
        source=_source_view(config) if config else None,
        inputs=inputs,
        missing_inputs=missing_inputs or [],
        blocking_components=blocking_components or [],
        components=components or [],
        final_amount=final_amount,
        assumptions=assumptions or [],
        limitations=limitations if limitations is not None else (list(config.source.limitations) if config else []),
    )


def quantize_money(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError("Tariff math requires Decimal.")
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def plain(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("Tariff math requires Decimal.")
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"
