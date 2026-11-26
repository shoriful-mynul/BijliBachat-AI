"""Calculation behavior, including synthetic fixtures that are not Pakistani tariffs."""

import ast
from decimal import Decimal
from pathlib import Path

from app.schemas.common import TrustStatus
from app.services.tariff_engine import calculate_tariff
from app.tariffs.loader import TariffCatalog, load_production_catalog
from app.tariffs.models import AvailabilityEntry
from tests.tariff_helpers import make_catalog, make_config, payload, request, unavailable_adjustment

ENGINE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "tariff_engine.py"
TARIFF_PACKAGE = Path(__file__).resolve().parents[1] / "app" / "tariffs"


def test_single_slab_applies_one_rate_to_total_consumption() -> None:
    config = make_config(
        slabs=[
            {"lower_exclusive_kwh": "0", "upper_inclusive_kwh": "100", "rate_per_kwh": "10.00"},
            {"lower_exclusive_kwh": "100", "upper_inclusive_kwh": None, "rate_per_kwh": "25.00"},
        ]
    )
    at_boundary = calculate_tariff(make_catalog(config), request(consumption_kwh="100"))
    above_boundary = calculate_tariff(make_catalog(config), request(consumption_kwh="100.001"))

    assert _amount(at_boundary, "energy_charge") == Decimal("1000.00")
    assert at_boundary.components[0].lines[0].rate_per_kwh == Decimal("10.00")
    assert _amount(above_boundary, "energy_charge") == Decimal("2500.03")
    assert above_boundary.components[0].lines[0].exact_amount == Decimal("2500.025")


def test_progressive_slabs_charge_each_band() -> None:
    config = _progressive()
    result = calculate_tariff(make_catalog(config), request(consumption_kwh="250"))

    assert _amount(result, "energy_charge") == Decimal("4500.00")
    assert [line.exact_amount for line in result.components[0].lines] == [
        Decimal("1000.00"),
        Decimal("2000.00"),
        Decimal("1500.00"),
    ]


def test_progressive_boundaries_stay_in_the_closed_band() -> None:
    catalog = make_catalog(_progressive())

    assert _amount(calculate_tariff(catalog, request(consumption_kwh="100")), "energy_charge") == Decimal("1000.00")
    assert _amount(calculate_tariff(catalog, request(consumption_kwh="100.001")), "energy_charge") == Decimal("1000.02")
    assert _amount(calculate_tariff(catalog, request(consumption_kwh="200")), "energy_charge") == Decimal("3000.00")
    assert _amount(calculate_tariff(catalog, request(consumption_kwh="0")), "energy_charge") == Decimal("0.00")


def test_one_previous_slab_is_not_progressive_and_not_single() -> None:
    config = _progressive(slab_method="one_previous_slab", config_id="synthetic-previous")
    result = calculate_tariff(make_catalog(config), request(consumption_kwh="250"))

    assert _amount(result, "energy_charge") == Decimal("5500.00")


def test_rounding_uses_half_up_on_the_component() -> None:
    config = make_config(
        slabs=[{"lower_exclusive_kwh": "0", "upper_inclusive_kwh": None, "rate_per_kwh": "1.015"}],
        adjustments=[
            {
                "code": "gst",
                "label": "Synthetic tax",
                "state": "applicable_verified",
                "required_for_payable": True,
                "basis": "percent_of_components",
                "percent": "10.00",
                "applies_to": ["energy_charge"],
                "reason": "Synthetic tax rate. Not a Pakistan tax.",
            }
        ],
    )
    result = calculate_tariff(make_catalog(config), request(consumption_kwh="3"))

    assert result.outcome == "calculated"
    assert result.trust_status == TrustStatus.CALCULATED
    assert _amount(result, "energy_charge") == Decimal("3.05")
    assert _amount(result, "gst") == Decimal("0.31")
    assert result.final_amount == Decimal("3.36")
    low = calculate_tariff(
        make_catalog(config),
        request(consumption_kwh="1"),
    )
    # 1 × 1.015 rounds half up to 1.02, not to 1.01.
    assert _amount(low, "energy_charge") == Decimal("1.02")


def test_complete_total_equals_the_component_sum() -> None:
    result = calculate_tariff(make_catalog(make_config()), request(consumption_kwh="10"))

    assert result.outcome == "calculated"
    assert result.final_amount == Decimal("118.00")
    assert sum(component.amount for component in result.components if component.amount is not None) == result.final_amount


def test_fixed_charge_uses_sanctioned_load_and_does_not_guess_when_missing() -> None:
    config = make_config(
        slabs=[
            {
                "lower_exclusive_kwh": "0",
                "upper_inclusive_kwh": None,
                "rate_per_kwh": "10.00",
                "fixed_charge_per_kw": "5.00",
            }
        ],
        fixed_charge={
            "state": "applicable_verified",
            "basis": "per_kw_of_sanctioned_load",
            "reason": "Synthetic fixed charge.",
        },
        adjustments=[
            {
                "code": "gst",
                "label": "Synthetic tax",
                "state": "applicable_verified",
                "required_for_payable": True,
                "basis": "percent_of_components",
                "percent": "18.00",
                "applies_to": ["energy_charge", "fixed_charge"],
                "reason": "Synthetic tax rate. Not a Pakistan tax.",
            }
        ],
    )
    present = calculate_tariff(
        make_catalog(config),
        request(consumption_kwh="10", sanctioned_load_kw="2"),
    )
    missing = calculate_tariff(make_catalog(config), request(consumption_kwh="10"))

    assert _amount(present, "energy_charge") == Decimal("100.00")
    assert _amount(present, "fixed_charge") == Decimal("10.00")
    assert _amount(present, "gst") == Decimal("19.80")
    assert present.final_amount == Decimal("129.80")
    assert missing.outcome == "unavailable"
    assert missing.trust_status == TrustStatus.UNAVAILABLE
    assert missing.final_amount is None
    assert missing.missing_inputs == ["sanctioned_load_kw"]
    assert _amount(missing, "fixed_charge") is None
    assert _amount(missing, "energy_charge") == Decimal("100.00")


def test_time_of_use_requires_both_periods() -> None:
    config = _tou()
    present = calculate_tariff(
        make_catalog(config),
        request(
            tariff_type="tou",
            eligibility=None,
            consumption_kwh="30",
            peak_kwh="10",
            off_peak_kwh="20",
            sanctioned_load_kw="6",
            maximum_demand_kw="4",
        ),
    )
    missing = calculate_tariff(
        make_catalog(config),
        request(
            tariff_type="tou",
            eligibility=None,
            consumption_kwh="30",
            sanctioned_load_kw="6",
            maximum_demand_kw="4",
        ),
    )

    assert _amount(present, "energy_charge") == Decimal("1000.00")
    assert _amount(present, "fixed_charge") == Decimal("2700.00")
    assert missing.missing_inputs == ["peak_kwh", "off_peak_kwh"]
    assert _amount(missing, "energy_charge") is None
    assert missing.final_amount is None
    assert missing.trust_status == TrustStatus.UNAVAILABLE


def test_time_of_use_rejects_a_split_that_does_not_match_consumption() -> None:
    result = calculate_tariff(
        make_catalog(_tou()),
        request(
            tariff_type="tou",
            eligibility=None,
            consumption_kwh="30",
            peak_kwh="10",
            off_peak_kwh="10",
            sanctioned_load_kw="6",
        ),
    )

    assert result.reason_code == "inconsistent_inputs"
    assert result.components == []
    assert result.final_amount is None


def test_missing_tax_is_not_stored_as_zero_and_blocks_the_payable_total() -> None:
    config = make_config(adjustments=[unavailable_adjustment()])
    result = calculate_tariff(make_catalog(config), request(consumption_kwh="10"))

    assert result.outcome == "unavailable"
    assert result.trust_status == TrustStatus.UNAVAILABLE
    assert result.final_amount is None
    assert result.reason_code == "incomplete_components"
    gst = next(component for component in result.components if component.code == "gst")
    assert gst.amount is None
    assert gst.trust_status == TrustStatus.UNAVAILABLE
    assert _amount(result, "energy_charge") == Decimal("100.00")


def test_unverified_configuration_produces_no_amounts() -> None:
    source = dict(payload()["source"])
    source["verification_status"] = "unverified"
    config = make_config(verification_status="unverified", source=source)
    result = calculate_tariff(make_catalog(config), request())

    assert result.reason_code == "unverified_configuration"
    assert result.components == []
    assert result.final_amount is None
    assert result.trust_status == TrustStatus.UNAVAILABLE


def test_expired_configuration_is_not_a_fallback() -> None:
    expired = make_config(config_id="synthetic-expired", effective_to="2026-05-31")
    other_company = make_config(
        config_id="synthetic-other",
        provider_code="OTHER",
        slabs=[{"lower_exclusive_kwh": "0", "upper_inclusive_kwh": None, "rate_per_kwh": "99.00"}],
    )
    result = calculate_tariff(
        make_catalog(expired, other_company),
        request(billing_date="2026-06-01", consumption_kwh="10"),
    )

    assert result.reason_code == "no_applicable_configuration"
    assert result.config_id is None
    assert result.final_amount is None
    assert result.components == []
    assert "99.00" not in result.reason


def test_ambiguous_configurations_are_not_averaged() -> None:
    first = make_config(config_id="synthetic-a")
    second = make_config(config_id="synthetic-b")
    result = calculate_tariff(TariffCatalog(configs=(first, second), availability=()), request())

    assert result.reason_code == "ambiguous_configuration"
    assert result.components == []
    assert result.final_amount is None


def test_unsupported_provider_does_not_borrow_another_schedule() -> None:
    result = calculate_tariff(make_catalog(make_config()), request(provider_code="HESCO"))

    assert result.reason_code == "unsupported_provider"
    assert result.config_id is None
    assert result.final_amount is None
    assert "10.00" not in result.reason


def test_unknown_category_is_not_replaced_with_residential() -> None:
    note = AvailabilityEntry.model_validate(
        {
            "provider_code": "SYNTH",
            "consumer_category": "residential",
            "status": "unavailable",
            "reason": "Only the synthetic residential fixture is loaded.",
            "source_url": "https://example.com/synthetic-tariff-fixture",
            "retrieval_date": "2026-01-02",
            "limitations": ["Synthetic fixture. Not a Pakistani tariff."],
        }
    )
    catalog = TariffCatalog(configs=(make_config(),), availability=(note,))
    result = calculate_tariff(catalog, request(consumer_category="commercial"))

    assert result.reason_code == "unknown_category"
    assert result.final_amount is None
    assert result.components == []


def test_eligibility_is_not_inferred_from_consumption() -> None:
    low = calculate_tariff(load_production_catalog(), _iesco(consumption_kwh="40", eligibility=None))
    high = calculate_tariff(load_production_catalog(), _iesco(consumption_kwh="250", eligibility=None))

    assert low.reason_code == high.reason_code == "missing_input"
    assert low.missing_inputs == ["eligibility"]
    assert low.components == []
    assert high.components == []
    assert low.final_amount is None


def test_protected_status_is_not_calculated_or_inferred() -> None:
    result = calculate_tariff(
        load_production_catalog(),
        _iesco(consumption_kwh="40", eligibility="protected"),
    )

    assert result.reason_code == "needs_verification"
    assert result.components == []
    assert result.final_amount is None
    assert result.trust_status == TrustStatus.UNAVAILABLE
    assert "158.00" not in result.reason


def test_iesco_unprotected_uses_one_row_for_every_unit() -> None:
    catalog = load_production_catalog()
    two_hundred = calculate_tariff(catalog, _iesco(consumption_kwh="200", sanctioned_load_kw="1"))
    two_fifty = calculate_tariff(catalog, _iesco(consumption_kwh="250", sanctioned_load_kw="5"))
    seven_hundred = calculate_tariff(catalog, _iesco(consumption_kwh="700", sanctioned_load_kw="1"))
    above = calculate_tariff(catalog, _iesco(consumption_kwh="700.001", sanctioned_load_kw="1"))

    assert _amount(two_hundred, "energy_charge") == Decimal("5782.00")
    assert _amount(two_hundred, "fixed_charge") == Decimal("300.00")
    assert two_hundred.components[0].lines[0].rate_per_kwh == Decimal("28.91")
    assert _amount(two_fifty, "energy_charge") == Decimal("8275.00")
    assert _amount(two_fifty, "fixed_charge") == Decimal("1750.00")
    assert _amount(seven_hundred, "energy_charge") == Decimal("29295.00")
    assert above.components[0].lines[0].exact_amount == Decimal("33040.0472")
    assert _amount(above, "energy_charge") == Decimal("33040.05")
    for result in (two_hundred, two_fifty, seven_hundred, above):
        assert result.outcome == "unavailable"
        assert result.final_amount is None
        assert result.trust_status == TrustStatus.UNAVAILABLE
        assert _amount(result, "gst") is None


def test_iesco_lifeline_bands_and_zero_consumption_minimum() -> None:
    catalog = load_production_catalog()
    forty = calculate_tariff(catalog, _iesco(consumption_kwh="40", eligibility="lifeline"))
    fifty = calculate_tariff(catalog, _iesco(consumption_kwh="50", eligibility="lifeline"))
    just_over = calculate_tariff(catalog, _iesco(consumption_kwh="50.001", eligibility="lifeline"))
    too_high = calculate_tariff(catalog, _iesco(consumption_kwh="100.001", eligibility="lifeline"))
    zero = calculate_tariff(catalog, _iesco(consumption_kwh="0", eligibility="lifeline", phase="single"))
    three_phase = calculate_tariff(catalog, _iesco(consumption_kwh="0", eligibility="lifeline", phase="three"))
    missing_phase = calculate_tariff(catalog, _iesco(consumption_kwh="0", eligibility="lifeline"))

    assert _amount(forty, "energy_charge") == Decimal("158.00")
    assert _amount(fifty, "energy_charge") == Decimal("197.50")
    assert just_over.components[0].lines[0].exact_amount == Decimal("387.00774")
    assert _amount(just_over, "energy_charge") == Decimal("387.01")
    assert too_high.reason_code == "consumption_not_covered"
    assert _amount(too_high, "energy_charge") is None
    assert too_high.config_id.endswith("lifeline-sro-279-2026")
    assert _amount(zero, "energy_charge") == Decimal("0.00")
    assert _amount(zero, "minimum_charge") == Decimal("75.00")
    assert _amount(three_phase, "minimum_charge") == Decimal("150.00")
    assert zero.final_amount is None
    assert missing_phase.missing_inputs == ["phase"]
    assert _amount(missing_phase, "minimum_charge") is None


def test_iesco_unprotected_zero_consumption_does_not_invent_a_slab() -> None:
    result = calculate_tariff(
        load_production_catalog(),
        _iesco(consumption_kwh="0", sanctioned_load_kw="5"),
    )

    assert result.reason_code == "consumption_not_covered"
    assert _amount(result, "fixed_charge") is None
    assert result.final_amount is None


def test_iesco_time_of_use_fixed_charge_follows_the_february_note() -> None:
    catalog = load_production_catalog()
    february = calculate_tariff(catalog, _tou_request(billing_date="2026-02-20"))
    march = calculate_tariff(catalog, _tou_request(billing_date="2026-03-01"))
    with_mdi = calculate_tariff(
        catalog,
        _tou_request(billing_date="2026-03-01", maximum_demand_kw="4"),
    )
    half_wins = calculate_tariff(
        catalog,
        _tou_request(billing_date="2026-03-01", maximum_demand_kw="2"),
    )

    assert _amount(february, "energy_charge") == Decimal("1159.10")
    assert _amount(february, "fixed_charge") == Decimal("2025.00")
    assert february.assumptions
    assert march.missing_inputs == ["maximum_demand_kw"]
    assert _amount(march, "fixed_charge") is None
    assert _amount(march, "energy_charge") == Decimal("1159.10")
    assert _amount(with_mdi, "fixed_charge") == Decimal("2700.00")
    assert _amount(half_wins, "fixed_charge") == Decimal("2025.00")
    assert february.final_amount is None


def test_a_billing_date_before_the_sro_does_not_use_it() -> None:
    result = calculate_tariff(
        load_production_catalog(),
        _iesco(billing_date="2026-02-11", sanctioned_load_kw="5"),
    )

    assert result.reason_code == "no_applicable_configuration"
    assert result.config_id is None
    assert result.components == []


def test_lesco_and_ke_are_unavailable_and_do_not_receive_iesco_rates() -> None:
    catalog = load_production_catalog()
    lesco = calculate_tariff(catalog, _iesco(provider_code="LESCO", sanctioned_load_kw="5"))
    ke = calculate_tariff(catalog, _iesco(provider_code="KE", sanctioned_load_kw="5"))

    for result in (lesco, ke):
        assert result.reason_code == "no_applicable_configuration"
        assert result.config_id is None
        assert result.components == []
        assert result.final_amount is None
        assert "8275" not in result.reason
        assert "22.44" not in result.reason


def test_calculation_path_has_no_binary_float_literals() -> None:
    for path in (ENGINE_PATH, *TARIFF_PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                raise AssertionError(f"{path.name} contains a float literal.")
            called = node.func if isinstance(node, ast.Call) else None
            if isinstance(called, ast.Name) and called.id == "float":
                raise AssertionError(f"{path.name} calls float().")


def _progressive(**overrides: object):
    body: dict[str, object] = {
        "config_id": "synthetic-progressive",
        "slab_method": "progressive_marginal",
        "slabs": [
            {"lower_exclusive_kwh": "0", "upper_inclusive_kwh": "100", "rate_per_kwh": "10.00"},
            {"lower_exclusive_kwh": "100", "upper_inclusive_kwh": "200", "rate_per_kwh": "20.00"},
            {"lower_exclusive_kwh": "200", "upper_inclusive_kwh": None, "rate_per_kwh": "30.00"},
        ],
    }
    body.update(overrides)
    return make_config(**body)


def _tou():
    return make_config(
        config_id="synthetic-tou",
        tariff_type="tou",
        eligibility=None,
        slab_method="time_of_use",
        slabs=[],
        time_of_use={"peak_rate_per_kwh": "40.00", "off_peak_rate_per_kwh": "30.00"},
        fixed_charge={
            "state": "applicable_verified",
            "basis": "higher_of_half_sanctioned_load_or_mdi",
            "rate_per_kw": "675.00",
            "reason": "Synthetic time-of-use fixed charge.",
        },
        adjustments=[unavailable_adjustment()],
    )


def _iesco(**overrides: object):
    body = {
        "provider_code": "IESCO",
        "consumer_category": "residential",
        "tariff_type": "non_tou",
        "eligibility": "unprotected",
        "billing_date": "2026-03-01",
        "consumption_kwh": "100",
    }
    body.update(overrides)
    return request(**body)


def _tou_request(**overrides: object):
    body = {
        "provider_code": "IESCO",
        "consumer_category": "residential",
        "tariff_type": "tou",
        "eligibility": None,
        "billing_date": "2026-03-01",
        "consumption_kwh": "30",
        "peak_kwh": "10",
        "off_peak_kwh": "20",
        "sanctioned_load_kw": "6",
    }
    body.update(overrides)
    return request(**body)


def _amount(result, code: str) -> Decimal | None:
    component = next(item for item in result.components if item.code == code)
    return component.amount
