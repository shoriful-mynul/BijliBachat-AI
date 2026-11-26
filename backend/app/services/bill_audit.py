"""Compare a confirmed bill with the tariff engine. Formulas stay in the engine."""

from datetime import UTC, datetime
from decimal import Decimal

from app.schemas.bill import BillAuditReport, ComparisonRow, ConfirmedBillRequest
from app.schemas.common import TrustStatus
from app.schemas.tariff import TariffCalculationRequest, TariffCalculationResponse
from app.services.tariff_engine import calculate_tariff
from app.tariffs.loader import TariffCatalog

COMPARISON_TOLERANCE = Decimal("1.00")

_BILL_COMPONENTS = (
    ("energy_charge", "Energy charges", "energy_charge"),
    ("fixed_charge", "Fixed charges", "fixed_charge"),
    ("fuel_price_adjustment", "Fuel price adjustment", "fuel_price_adjustment"),
    ("gst", "GST", "gst"),
    ("electricity_duty", "Electricity duty", "electricity_duty"),
    ("tv_fee", "TV fee", "tv_fee"),
    ("minimum_charge", "Minimum charge", None),
)

_PAYABLE_EXPLANATION = (
    "A complete payable-bill comparison is unavailable. "
    "Taxes, duty, fuel adjustment, or another required component is not in the tariff result, "
    "so the bill total was not compared with a partial subtotal."
)


def audit_confirmed_bill(catalog: TariffCatalog, bill: ConfirmedBillRequest) -> BillAuditReport:
    request = TariffCalculationRequest(
        provider_code=bill.provider_code,
        consumer_category=bill.consumer_category,
        tariff_type=bill.tariff_type,
        eligibility=bill.eligibility,
        billing_date=bill.billing_date,
        consumption_kwh=bill.consumption_kwh,
        peak_kwh=bill.peak_kwh,
        off_peak_kwh=bill.off_peak_kwh,
        sanctioned_load_kw=bill.sanctioned_load_kw,
        maximum_demand_kw=bill.maximum_demand_kw,
        phase=bill.phase,
    )
    result = calculate_tariff(catalog, request)
    calculated = {component.code: component for component in result.components}
    rows = [
        _compare(code, label, getattr(bill, attr) if attr else None, calculated.get(code))
        for code, label, attr in _BILL_COMPONENTS
    ]
    for charge in bill.other_charges:
        rows.append(
            ComparisonRow(
                code="other_charge",
                label=charge.label,
                reported_amount=_money(charge.amount),
                outcome="not_comparable",
                trust_status=TrustStatus.UNAVAILABLE,
                explanation=(
                    "This printed charge has no equivalent component in the tariff result, "
                    "so it was not treated as a mismatch."
                ),
            )
        )
    if bill.arrears is not None:
        rows.append(
            ComparisonRow(
                code="arrears",
                label="Arrears",
                reported_amount=_money(bill.arrears),
                outcome="not_comparable",
                trust_status=TrustStatus.UNAVAILABLE,
                explanation="Arrears are carried forward and are not a tariff component.",
            )
        )
    complete = _payable_comparison_is_complete(bill, result)
    rows.append(_total_row(bill, result, complete))
    limitations = [
        f"Amounts within {COMPARISON_TOLERANCE} PKR are treated as a match. "
        "This is an audit tolerance, not a tariff rule.",
        *result.limitations,
    ]
    if not complete:
        limitations.append(_PAYABLE_EXPLANATION)
    mismatches = [row.label for row in rows if row.outcome == "possible_mismatch"]
    if mismatches:
        explanation = (
            "Possible mismatch on " + ", ".join(mismatches) + ". "
            "Only those components were compared."
        )
    elif complete:
        explanation = "The confirmed payable amount agrees with the calculated payable amount."
    else:
        explanation = result.reason if result.outcome != "calculated" else _PAYABLE_EXPLANATION
    return BillAuditReport(
        provider_code=result.provider_code,
        consumer_category=result.consumer_category,
        tariff_type=result.tariff_type,
        eligibility=result.eligibility,
        billing_period=bill.billing_date,
        confirmed="user_confirmed",
        config_id=result.config_id,
        config_version=result.config_version,
        source=result.source,
        comparisons=rows,
        missing_inputs=result.missing_inputs,
        blocking_components=result.blocking_components,
        limitations=limitations,
        complete_payable_comparison=complete,
        overall_trust_status=TrustStatus.UNAVAILABLE if not complete else TrustStatus.CALCULATED,
        explanation=explanation,
        calculated_at=datetime.now(UTC),
    )


def _compare(code: str, label: str, reported: Decimal | None, component: object | None) -> ComparisonRow:
    calculated = getattr(component, "amount", None) if component is not None else None
    state = getattr(component, "state", None)
    if reported is None:
        return ComparisonRow(
            code=code,
            label=label,
            calculated_amount=_money(calculated),
            outcome="not_comparable",
            trust_status=TrustStatus.UNAVAILABLE,
            explanation=f"The confirmed bill does not include {label.lower()}, so it was not treated as zero.",
        )
    if calculated is None or state == "unavailable":
        return ComparisonRow(
            code=code,
            label=label,
            reported_amount=_money(reported),
            outcome="unavailable",
            trust_status=TrustStatus.UNAVAILABLE,
            explanation=(
                f"The tariff result does not include {label.lower()}, "
                "so the confirmed amount was not judged."
            ),
        )
    difference = reported - calculated
    outcome = "match" if abs(difference) <= COMPARISON_TOLERANCE else "possible_mismatch"
    if outcome == "match":
        explanation = f"The confirmed {label.lower()} agrees with the calculated amount within 1.00 PKR."
    else:
        explanation = (
            f"Possible mismatch. The confirmed {label.lower()} is {_money(reported)} PKR "
            f"and the calculated amount is {_money(calculated)} PKR. "
            f"The difference is {_money(difference)} PKR."
        )
    return ComparisonRow(
        code=code,
        label=label,
        reported_amount=_money(reported),
        calculated_amount=_money(calculated),
        difference=_money(difference),
        outcome=outcome,
        trust_status=TrustStatus.CALCULATED,
        explanation=explanation,
    )


def _total_row(bill: ConfirmedBillRequest, result: TariffCalculationResponse, complete: bool) -> ComparisonRow:
    if not complete:
        return ComparisonRow(
            code="total_amount_due",
            label="Total amount due",
            reported_amount=_money(bill.total_amount_due),
            outcome="not_comparable",
            trust_status=TrustStatus.UNAVAILABLE,
            explanation=_PAYABLE_EXPLANATION,
        )
    difference = bill.total_amount_due - result.final_amount  # type: ignore[operator]
    outcome = "match" if abs(difference) <= COMPARISON_TOLERANCE else "possible_mismatch"
    explanation = (
        "The confirmed payable amount agrees with the calculated payable amount within 1.00 PKR."
        if outcome == "match"
        else (
            "Possible mismatch. The confirmed payable amount differs from the calculated payable amount "
            f"by {_money(difference)} PKR."
        )
    )
    return ComparisonRow(
        code="total_amount_due",
        label="Total amount due",
        reported_amount=_money(bill.total_amount_due),
        calculated_amount=_money(result.final_amount),
        difference=_money(difference),
        outcome=outcome,
        trust_status=TrustStatus.CALCULATED,
        explanation=explanation,
    )


def _payable_comparison_is_complete(bill: ConfirmedBillRequest, result: TariffCalculationResponse) -> bool:
    return (
        result.outcome == "calculated"
        and result.final_amount is not None
        and bill.total_amount_due is not None
        and bill.arrears is None
        and not bill.other_charges
        and not result.blocking_components
    )


def _money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value:.2f}"
