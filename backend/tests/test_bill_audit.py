from decimal import Decimal

from app.schemas.bill import ConfirmedBillRequest
from app.schemas.common import TrustStatus
from app.services.bill_audit import audit_confirmed_bill
from app.tariffs.loader import load_production_catalog
from tests.tariff_helpers import make_catalog, make_config

CATALOG = load_production_catalog()


def confirmed(**overrides: object) -> ConfirmedBillRequest:
    body = {
        "confirmation": "user_confirmed",
        "provider_code": "IESCO",
        "consumer_category": "residential",
        "tariff_type": "non_tou",
        "eligibility": "unprotected",
        "billing_date": "2026-03-01",
        "consumption_kwh": "250",
        "sanctioned_load_kw": "5",
        "energy_charge": "8275.00",
        "fixed_charge": "1750.00",
        "total_amount_due": "12000.00",
    }
    body.update(overrides)
    return ConfirmedBillRequest.model_validate(body)


def row(report, code: str):
    return next(item for item in report.comparisons if item.code == code)


def test_matching_energy_and_fixed_charges_do_not_audit_the_payable_total() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed())

    assert report.config_id is not None
    assert report.config_version is not None
    assert report.source is not None
    assert report.complete_payable_comparison is False
    assert report.overall_trust_status == TrustStatus.UNAVAILABLE
    assert row(report, "energy_charge").outcome == "match"
    assert row(report, "fixed_charge").outcome == "match"
    assert row(report, "total_amount_due").outcome == "not_comparable"
    assert row(report, "total_amount_due").calculated_amount is None
    assert "partial subtotal" in row(report, "total_amount_due").explanation


def test_possible_mismatch_uses_the_confirmed_amount() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(energy_charge="9000.00"))
    energy = row(report, "energy_charge")

    assert energy.outcome == "possible_mismatch"
    assert energy.reported_amount == "9000.00"
    assert energy.calculated_amount == "8275.00"
    assert "Possible mismatch" in energy.explanation
    assert "fraud" not in energy.explanation.lower()


def test_a_small_difference_inside_the_documented_tolerance_matches() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(energy_charge="8275.50"))
    assert row(report, "energy_charge").outcome == "match"


def test_missing_bill_component_is_not_a_mismatch_and_is_not_zero() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(gst=None, fuel_price_adjustment=None))

    assert row(report, "gst").outcome == "not_comparable"
    assert row(report, "gst").reported_amount is None
    assert row(report, "fuel_price_adjustment").outcome == "not_comparable"


def test_a_printed_tax_is_unavailable_when_the_tariff_has_no_tax() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(gst="500.00"))
    gst = row(report, "gst")

    assert gst.outcome == "unavailable"
    assert gst.calculated_amount is None
    assert gst.difference is None
    assert gst.outcome != "possible_mismatch"


def test_missing_required_inputs_do_not_invent_a_comparison() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(eligibility=None, sanctioned_load_kw=None))

    assert "eligibility" in report.missing_inputs
    assert row(report, "energy_charge").outcome == "unavailable"
    assert row(report, "energy_charge").calculated_amount is None


def test_another_provider_does_not_use_the_iesco_tariff() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(provider_code="LESCO"))

    assert report.config_id is None
    assert row(report, "energy_charge").calculated_amount is None
    assert "8275.00" not in row(report, "energy_charge").explanation
    hesco = audit_confirmed_bill(CATALOG, confirmed(provider_code="HESCO"))
    assert hesco.config_id is None
    assert row(hesco, "energy_charge").calculated_amount is None


def test_a_date_before_the_schedule_does_not_fall_back() -> None:
    report = audit_confirmed_bill(CATALOG, confirmed(billing_date="2026-02-11"))
    assert report.config_id is None
    assert row(report, "energy_charge").outcome == "unavailable"


def test_complete_synthetic_payable_comparison_is_separate_from_production(monkeypatch) -> None:
    catalog = make_catalog(make_config())
    bill = confirmed(
        provider_code="SYNTH",
        consumption_kwh="10",
        energy_charge="100.00",
        fixed_charge=None,
        gst="18.00",
        total_amount_due="118.00",
        sanctioned_load_kw=None,
    )
    report = audit_confirmed_bill(catalog, bill)

    assert report.complete_payable_comparison is True
    assert report.overall_trust_status == TrustStatus.CALCULATED
    assert row(report, "total_amount_due").outcome == "match"
    assert row(report, "total_amount_due").calculated_amount == "118.00"
    production = audit_confirmed_bill(CATALOG, confirmed())
    assert production.complete_payable_comparison is False
