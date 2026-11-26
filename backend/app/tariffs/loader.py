"""Load tariff files and reject a catalog that contradicts itself."""

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from app.tariffs.models import AvailabilityEntry, TariffConfig, TariffConfigError

PACKAGE_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class TariffCatalog:
    configs: tuple[TariffConfig, ...]
    availability: tuple[AvailabilityEntry, ...]


def load_production_catalog() -> TariffCatalog:
    """Load the files shipped with the API. Synthetic fixtures are rejected."""
    return load_catalog(
        PACKAGE_ROOT / "configs",
        PACKAGE_ROOT / "availability.json",
        allow_synthetic=False,
    )


def load_catalog(
    config_dir: Path,
    availability_path: Path,
    *,
    allow_synthetic: bool,
) -> TariffCatalog:
    if not config_dir.is_dir():
        raise TariffConfigError(f"Tariff directory does not exist: {config_dir.name}.")
    configs = tuple(
        _load_config(path, allow_synthetic=allow_synthetic)
        for path in sorted(config_dir.glob("*.json"))
    )
    _reject_duplicate_ids(configs)
    _reject_overlapping_scopes(configs)
    availability = _load_availability(availability_path)
    return TariffCatalog(configs=configs, availability=availability)


def parse_tariff_document(text: str) -> object:
    """Parse JSON without turning a rate into a binary float."""

    def parse_number(token: str) -> Decimal:
        if "e" in token.lower():
            raise TariffConfigError("Scientific notation is not accepted in a tariff file.")
        return Decimal(token)

    try:
        document = json.loads(text, parse_float=parse_number)
    except json.JSONDecodeError as exc:
        raise TariffConfigError("Tariff file is not valid JSON.") from exc
    _reject_binary_floats(document)
    return document


def _load_config(path: Path, *, allow_synthetic: bool) -> TariffConfig:
    document = parse_tariff_document(path.read_text(encoding="utf-8"))
    try:
        config = TariffConfig.model_validate(document)
    except ValidationError as exc:
        raise TariffConfigError(_validation_message(path.name, exc)) from exc
    if config.synthetic and not allow_synthetic:
        raise TariffConfigError(
            f"{path.name} is marked synthetic and cannot be loaded as a production tariff."
        )
    return config


def _load_availability(path: Path) -> tuple[AvailabilityEntry, ...]:
    if not path.is_file():
        raise TariffConfigError("The tariff availability file is missing.")
    document = parse_tariff_document(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or "entries" not in document:
        raise TariffConfigError("The tariff availability file must contain an entries list.")
    try:
        entries = [AvailabilityEntry.model_validate(item) for item in document["entries"]]
    except (ValidationError, TypeError) as exc:
        message = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else "invalid entry"
        raise TariffConfigError(f"The tariff availability file is invalid: {message}.") from exc
    return tuple(entries)


def _reject_duplicate_ids(configs: tuple[TariffConfig, ...]) -> None:
    seen: set[str] = set()
    for config in configs:
        if config.config_id in seen:
            raise TariffConfigError(f"Tariff configuration id {config.config_id} is repeated.")
        seen.add(config.config_id)


def _reject_overlapping_scopes(configs: tuple[TariffConfig, ...]) -> None:
    for index, config in enumerate(configs):
        for other in configs[index + 1 :]:
            if config.scope_key() != other.scope_key():
                continue
            if _ranges_overlap(config, other):
                raise TariffConfigError(
                    "Tariff configurations "
                    f"{config.config_id} and {other.config_id} overlap for the same scope."
                )


def _ranges_overlap(left: TariffConfig, right: TariffConfig) -> bool:
    left_end = left.effective_to or date.max
    right_end = right.effective_to or date.max
    return left.effective_from <= right_end and right.effective_from <= left_end


def _reject_binary_floats(value: object) -> None:
    if isinstance(value, float):
        raise TariffConfigError("A tariff file contains a binary float.")
    if isinstance(value, dict):
        for item in value.values():
            _reject_binary_floats(item)
    elif isinstance(value, list):
        for item in value:
            _reject_binary_floats(item)


def _validation_message(filename: str, exc: ValidationError) -> str:
    details = "; ".join(str(error["msg"]) for error in exc.errors()[:5])
    return f"{filename} is not a valid tariff configuration: {details}."
