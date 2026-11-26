"""Tariff file validation. Production rates are checked against the IESCO guide."""

import json
from pathlib import Path

import pytest

from app.tariffs.loader import TariffConfigError, load_catalog, load_production_catalog, parse_tariff_document
from app.tariffs.models import TariffConfig
from tests.tariff_helpers import payload

CONFIG_DIR = Path(__file__).resolve().parents[1] / "app" / "tariffs" / "configs"

UNPROTECTED_RATES = [
    ("0", "100", "22.44", "275.00"),
    ("100", "200", "28.91", "300.00"),
    ("200", "300", "33.10", "350.00"),
    ("300", "400", "36.46", "400.00"),
    ("400", "500", "38.95", "500.00"),
    ("500", "600", "40.22", "675.00"),
    ("600", "700", "41.85", "675.00"),
    ("700", None, "47.20", "675.00"),
]


def test_production_catalog_loads_only_verified_iesco_files() -> None:
    catalog = load_production_catalog()

    assert [config.provider_code for config in catalog.configs] == ["IESCO", "IESCO", "IESCO"]
    assert {config.synthetic for config in catalog.configs} == {False}
    assert {config.verification_status for config in catalog.configs} == {"verified"}
    assert all(config.source.source_url == "https://iesco.com.pk/tariff-guide" for config in catalog.configs)
    assert all(config.source.retrieval_date.isoformat() == "2026-11-26" for config in catalog.configs)
    assert all(config.effective_from.isoformat() == "2026-02-12" for config in catalog.configs)
    assert all(config.effective_to is None for config in catalog.configs)
    providers = {entry.provider_code for entry in catalog.availability}
    assert providers == {"IESCO", "LESCO", "KE"}


def test_production_rates_match_the_iesco_tariff_guide() -> None:
    catalog = load_production_catalog()
    by_id = {config.config_id: config for config in catalog.configs}

    lifeline = by_id["iesco-a1-residential-non-tou-lifeline-sro-279-2026"]
    assert lifeline.slab_method == "single_slab"
    assert [(str(slab.lower_exclusive_kwh), str(slab.upper_inclusive_kwh), str(slab.rate_per_kwh)) for slab in lifeline.slabs] == [
        ("0", "50", "3.95"),
        ("50", "100", "7.74"),
    ]
    assert lifeline.fixed_charge.state == "not_applicable"
    assert lifeline.minimum_charge.single_phase_amount is not None
    assert str(lifeline.minimum_charge.single_phase_amount) == "75.00"
    assert str(lifeline.minimum_charge.three_phase_amount) == "150.00"

    unprotected = by_id["iesco-a1-residential-non-tou-unprotected-sro-279-2026"]
    assert unprotected.slab_method == "single_slab"
    assert [
        (
            str(slab.lower_exclusive_kwh),
            None if slab.upper_inclusive_kwh is None else str(slab.upper_inclusive_kwh),
            str(slab.rate_per_kwh),
            str(slab.fixed_charge_per_kw),
        )
        for slab in unprotected.slabs
    ] == UNPROTECTED_RATES

    tou = by_id["iesco-a1-residential-tou-sro-279-2026"]
    assert tou.slab_method == "time_of_use"
    assert tou.time_of_use is not None
    assert str(tou.time_of_use.peak_rate_per_kwh) == "46.85"
    assert str(tou.time_of_use.off_peak_rate_per_kwh) == "34.53"
    assert str(tou.fixed_charge.rate_per_kw) == "675.00"
    for config in catalog.configs:
        assert {item.code: item.state for item in config.adjustments} == {
            "gst": "unavailable",
            "fuel_price_adjustment": "unavailable",
            "electricity_duty": "unavailable",
            "tv_fee": "unavailable",
        }


def test_production_files_do_not_carry_secrets() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in CONFIG_DIR.glob("*.json"))
    text += (CONFIG_DIR.parent / "availability.json").read_text(encoding="utf-8")
    lowered = text.lower()
    for forbidden in ("api_key", "secret", "password", "private_key", "begin private"):
        assert forbidden not in lowered


def test_invalid_json_is_rejected(tmp_path: Path) -> None:
    config_dir, availability = _write_catalog(tmp_path, ["{not json"])

    with pytest.raises(TariffConfigError, match="not valid JSON"):
        load_catalog(config_dir, availability, allow_synthetic=True)


def test_scientific_notation_is_rejected() -> None:
    with pytest.raises(TariffConfigError, match="Scientific notation"):
        parse_tariff_document('{"rate": 1e2}')


def test_missing_required_metadata_is_rejected() -> None:
    document = payload()
    del document["source"]

    with pytest.raises(ValueError):
        TariffConfig.model_validate(document)


def test_effective_end_before_start_is_rejected() -> None:
    with pytest.raises(ValueError, match="effective_to"):
        TariffConfig.model_validate(payload(effective_from="2026-02-01", effective_to="2026-01-01"))


def test_negative_rate_is_rejected() -> None:
    with pytest.raises(ValueError):
        TariffConfig.model_validate(
            payload(slabs=[{"lower_exclusive_kwh": "0", "upper_inclusive_kwh": None, "rate_per_kwh": "-1.00"}])
        )


def test_overlapping_slabs_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        TariffConfig.model_validate(
            payload(
                slabs=[
                    {"lower_exclusive_kwh": "0", "upper_inclusive_kwh": "100", "rate_per_kwh": "10.00"},
                    {"lower_exclusive_kwh": "50", "upper_inclusive_kwh": None, "rate_per_kwh": "20.00"},
                ]
            )
        )


def test_unsupported_calculation_method_is_rejected() -> None:
    with pytest.raises(ValueError):
        TariffConfig.model_validate(payload(slab_method="flat_average"))


def test_missing_calculation_method_is_rejected() -> None:
    document = payload()
    del document["slab_method"]

    with pytest.raises(ValueError):
        TariffConfig.model_validate(document)


def test_overlapping_configurations_are_rejected(tmp_path: Path) -> None:
    first = payload(config_id="synthetic-a")
    second = payload(config_id="synthetic-b", effective_from="2026-06-01")
    config_dir, availability = _write_catalog(tmp_path, [json.dumps(first), json.dumps(second)])

    with pytest.raises(TariffConfigError, match="overlap"):
        load_catalog(config_dir, availability, allow_synthetic=True)


def test_successive_versions_can_load(tmp_path: Path) -> None:
    first = payload(config_id="synthetic-old", effective_to="2026-05-31")
    second = payload(config_id="synthetic-new", effective_from="2026-06-01")
    config_dir, availability = _write_catalog(tmp_path, [json.dumps(first), json.dumps(second)])

    catalog = load_catalog(config_dir, availability, allow_synthetic=True)

    assert {config.config_id for config in catalog.configs} == {"synthetic-old", "synthetic-new"}


def test_synthetic_file_is_rejected_from_a_production_load(tmp_path: Path) -> None:
    config_dir, availability = _write_catalog(tmp_path, [json.dumps(payload())])

    with pytest.raises(TariffConfigError, match="synthetic"):
        load_catalog(config_dir, availability, allow_synthetic=False)


def test_unverified_status_cannot_disagree_with_the_source() -> None:
    source = dict(payload()["source"])
    source["verification_status"] = "unverified"

    with pytest.raises(ValueError, match="verification"):
        TariffConfig.model_validate(payload(verification_status="verified", source=source))


def _write_catalog(tmp_path: Path, documents: list[str]) -> tuple[Path, Path]:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    for index, document in enumerate(documents):
        (config_dir / f"{index}.json").write_text(document, encoding="utf-8")
    availability = tmp_path / "availability.json"
    availability.write_text('{"entries": []}', encoding="utf-8")
    return config_dir, availability
