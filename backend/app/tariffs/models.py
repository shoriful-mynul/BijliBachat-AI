"""Strict shape of a versioned tariff file.

A file describes one provider, category, tariff type, and eligibility for one
date range. Missing rates stay missing. They are not stored as zero.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from app.schemas.common import ApiModel, reject_unsafe_decimal_input

Rate = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(ge=0, max_digits=12, decimal_places=4),
]
KilowattBound = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(ge=0, max_digits=12, decimal_places=3),
]
RupeeRate = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(ge=0, max_digits=12, decimal_places=2),
]
PercentRate = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(ge=0, max_digits=8, decimal_places=4),
]

ComponentState = Literal[
    "applicable_verified",
    "not_applicable",
    "unavailable",
    "needs_verification",
]
SlabMethod = Literal[
    "single_slab",
    "progressive_marginal",
    "one_previous_slab",
    "time_of_use",
]
VerificationStatus = Literal[
    "verified",
    "unverified",
    "needs_verification",
    "incomplete",
]
BASE_COMPONENT_CODES = ("energy_charge", "fixed_charge", "minimum_charge")


class TariffConfigError(ValueError):
    """A tariff file or a set of files cannot be used."""


class Slab(ApiModel):
    """One consumption band. The lower bound is exclusive and the upper is inclusive."""

    lower_exclusive_kwh: KilowattBound
    upper_inclusive_kwh: KilowattBound | None = None
    rate_per_kwh: Rate
    fixed_charge_per_kw: RupeeRate | None = None

    @model_validator(mode="after")
    def upper_follows_lower(self) -> "Slab":
        if (
            self.upper_inclusive_kwh is not None
            and self.upper_inclusive_kwh <= self.lower_exclusive_kwh
        ):
            raise ValueError("A slab's upper bound must be greater than its lower bound.")
        return self


class RoundingPolicy(ApiModel):
    """How money components are finished. Intermediate products stay exact."""

    money_quantum: Literal["0.01"]
    mode: Literal["half_up"]
    stage: Literal["component"]
    source_status: Literal["engine_convention", "source_stated"]
    note: str = Field(min_length=1, max_length=500)


class SourceRecord(ApiModel):
    issuing_authority: str = Field(min_length=1, max_length=200)
    document_title: str = Field(min_length=1, max_length=200)
    source_url: str = Field(pattern=r"^https://[^\s]+$")
    notification_date: date | None = None
    retrieval_date: date
    reference: str = Field(min_length=1, max_length=300)
    verification_status: VerificationStatus
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "SourceRecord":
        if (
            self.notification_date is not None
            and self.notification_date > self.retrieval_date
        ):
            raise ValueError("The notification date cannot be after the retrieval date.")
        for note in self.limitations:
            if not note.strip():
                raise ValueError("A limitation note cannot be empty.")
        return self


class Adjustment(ApiModel):
    """A tax or other bill component. Its formula exists only when the state says so."""

    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40)
    label: str = Field(min_length=1, max_length=80)
    state: ComponentState
    required_for_payable: bool
    basis: Literal["percent_of_components", "flat_amount"] | None = None
    percent: PercentRate | None = None
    amount: RupeeRate | None = None
    applies_to: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def formula_matches_state(self) -> "Adjustment":
        if self.state == "not_applicable" and self.required_for_payable:
            raise ValueError("A component that does not apply cannot be required for a payable total.")
        if self.state != "applicable_verified":
            if self.basis is not None or self.percent is not None or self.amount is not None:
                raise ValueError("An unverified component cannot carry a rate or a formula.")
            if self.applies_to:
                raise ValueError("An unverified component cannot name a formula base.")
            return self
        if self.basis == "percent_of_components":
            if self.percent is None or not self.applies_to or self.amount is not None:
                raise ValueError("A percent component needs a percent and the components it uses.")
        elif self.basis == "flat_amount":
            if self.amount is None or self.percent is not None or self.applies_to:
                raise ValueError("A flat component needs an amount and no percent base.")
        else:
            raise ValueError("A verified component needs a supported formula.")
        unknown = [code for code in self.applies_to if code not in BASE_COMPONENT_CODES]
        if unknown:
            raise ValueError("A percent component can use only energy, fixed, or minimum charges.")
        if len(set(self.applies_to)) != len(self.applies_to):
            raise ValueError("A percent component repeats a base component.")
        return self


class FixedChargePolicy(ApiModel):
    state: ComponentState
    basis: Literal[
        "per_kw_of_sanctioned_load",
        "higher_of_half_sanctioned_load_or_mdi",
    ] | None = None
    rate_per_kw: RupeeRate | None = None
    mdi_optional_through: date | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def basis_matches_state(self) -> "FixedChargePolicy":
        if self.state != "applicable_verified":
            if self.basis is not None or self.rate_per_kw is not None or self.mdi_optional_through is not None:
                raise ValueError("A fixed charge without a verified rate cannot carry a formula.")
            return self
        if self.basis == "per_kw_of_sanctioned_load":
            if self.rate_per_kw is not None or self.mdi_optional_through is not None:
                raise ValueError("Per-slab fixed charges keep the rate on each slab.")
            return self
        if self.basis == "higher_of_half_sanctioned_load_or_mdi":
            if self.rate_per_kw is None:
                raise ValueError("This fixed-charge method needs a rupee per kW rate.")
            return self
        raise ValueError("A verified fixed charge needs a supported basis.")


class MinimumChargePolicy(ApiModel):
    state: ComponentState
    applies_when: Literal["zero_consumption"] | None = None
    single_phase_amount: RupeeRate | None = None
    three_phase_amount: RupeeRate | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def amounts_match_state(self) -> "MinimumChargePolicy":
        if self.state != "applicable_verified":
            if (
                self.applies_when is not None
                or self.single_phase_amount is not None
                or self.three_phase_amount is not None
            ):
                raise ValueError("An unverified minimum charge cannot carry an amount.")
            return self
        if (
            self.applies_when != "zero_consumption"
            or self.single_phase_amount is None
            or self.three_phase_amount is None
        ):
            raise ValueError("A verified minimum charge needs both phase amounts.")
        return self


class TimeOfUseRates(ApiModel):
    peak_rate_per_kwh: Rate
    off_peak_rate_per_kwh: Rate


class TariffConfig(ApiModel):
    config_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    version: str = Field(min_length=1, max_length=40)
    provider_code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=32)
    consumer_category: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=40)
    tariff_type: Literal["non_tou", "tou"]
    eligibility: Literal["lifeline", "protected", "unprotected"] | None = None
    schedule_name: str = Field(min_length=1, max_length=80)
    billing_frequency: Literal["monthly"]
    effective_from: date
    effective_to: date | None = None
    slab_method: SlabMethod
    verification_status: VerificationStatus
    synthetic: bool = False
    rounding: RoundingPolicy
    slabs: list[Slab] = Field(default_factory=list)
    fixed_charge: FixedChargePolicy
    minimum_charge: MinimumChargePolicy
    time_of_use: TimeOfUseRates | None = None
    adjustments: list[Adjustment] = Field(min_length=1)
    source: SourceRecord

    @model_validator(mode="after")
    def structure_is_consistent(self) -> "TariffConfig":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be earlier than effective_from.")
        if self.source.verification_status != self.verification_status:
            raise ValueError("The source verification status must match the configuration.")
        if self.tariff_type == "tou":
            if self.eligibility is not None:
                raise ValueError("A time-of-use file does not also carry a lifeline or protected label.")
        elif self.eligibility is None:
            raise ValueError("A non-time-of-use file must name the confirmed eligibility it applies to.")
        self._check_method()
        self._check_slabs()
        self._check_fixed_and_minimum()
        codes = [item.code for item in self.adjustments]
        if len(set(codes)) != len(codes):
            raise ValueError("An adjustment code is repeated.")
        return self

    def _check_method(self) -> None:
        if self.slab_method == "time_of_use":
            if self.time_of_use is None or self.slabs:
                raise ValueError("A time-of-use file needs peak and off-peak rates and no energy slabs.")
            return
        if self.time_of_use is not None or not self.slabs:
            raise ValueError("This slab method needs slabs and no time-of-use rates.")

    def _check_slabs(self) -> None:
        if self.slab_method == "time_of_use":
            return
        ordered = sorted(
            self.slabs,
            key=lambda slab: (slab.lower_exclusive_kwh, slab.upper_inclusive_kwh is None),
        )
        if [id(item) for item in ordered] != [id(item) for item in self.slabs]:
            raise ValueError("Slabs must be listed from the lowest band upward.")
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if earlier.upper_inclusive_kwh is None:
                raise ValueError("Only the last slab can be open-ended.")
            if later.lower_exclusive_kwh < earlier.upper_inclusive_kwh:
                raise ValueError("Slab bands overlap.")
        if self.slab_method in {"progressive_marginal", "one_previous_slab"}:
            if ordered[0].lower_exclusive_kwh != 0:
                raise ValueError("This slab method must start at zero.")
            for earlier, later in zip(ordered, ordered[1:], strict=False):
                if later.lower_exclusive_kwh != earlier.upper_inclusive_kwh:
                    raise ValueError("This slab method does not allow a gap between slabs.")
            if ordered[-1].upper_inclusive_kwh is not None:
                raise ValueError("This slab method needs an open-ended final slab.")

    def _check_fixed_and_minimum(self) -> None:
        per_slab = (
            self.fixed_charge.state == "applicable_verified"
            and self.fixed_charge.basis == "per_kw_of_sanctioned_load"
        )
        for slab in self.slabs:
            if per_slab and slab.fixed_charge_per_kw is None:
                raise ValueError("Each slab needs its own fixed charge per kW.")
            if not per_slab and slab.fixed_charge_per_kw is not None:
                raise ValueError("A slab carries a fixed charge the policy does not use.")
        tou_basis = self.fixed_charge.basis == "higher_of_half_sanctioned_load_or_mdi"
        if self.slab_method == "time_of_use" and self.fixed_charge.state == "applicable_verified" and not tou_basis:
            raise ValueError("A time-of-use fixed charge uses half the sanctioned load or MDI.")
        if self.slab_method != "time_of_use" and tou_basis:
            raise ValueError("That fixed-charge basis belongs on a time-of-use file.")
        fixed_applies = self.fixed_charge.state == "applicable_verified"
        minimum_applies = self.minimum_charge.state == "applicable_verified"
        if fixed_applies and minimum_applies:
            raise ValueError("Minimum and fixed charges cannot both apply in one file.")
        if self.fixed_charge.mdi_optional_through is not None and (
            self.fixed_charge.mdi_optional_through < self.effective_from
        ):
            raise ValueError("The MDI exception cannot end before the file takes effect.")

    def covers(self, billing_date: date) -> bool:
        if billing_date < self.effective_from:
            return False
        if self.effective_to is not None and billing_date > self.effective_to:
            return False
        return True

    def scope_key(self) -> tuple[str, str, str, str]:
        return (
            self.provider_code.casefold(),
            self.consumer_category.casefold(),
            self.tariff_type,
            self.eligibility or "",
        )


class AvailabilityEntry(ApiModel):
    """Why a provider or category has no calculable file. This is not a rate table."""

    provider_code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=32)
    consumer_category: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]*$", max_length=40)
    tariff_type: Literal["non_tou", "tou"] | None = None
    eligibility: Literal["lifeline", "protected", "unprotected"] | None = None
    status: Literal["unavailable", "needs_verification"]
    reason: str = Field(min_length=1, max_length=800)
    source_url: str | None = Field(default=None, pattern=r"^https://[^\s]+$")
    retrieval_date: date
    limitations: list[str] = Field(min_length=1)
