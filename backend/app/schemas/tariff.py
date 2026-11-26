"""Tariff inspection and calculation contracts.

Amounts are Decimal values. A missing amount stays null. It is not zero.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from app.schemas.common import ApiModel, KilowattHours, MoneyAmount, TrustStatus, reject_unsafe_decimal_input
from app.tariffs.models import ComponentState, VerificationStatus

ExactDecimal = Annotated[Decimal, BeforeValidator(reject_unsafe_decimal_input)]
LoadKilowatts = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(gt=0, max_digits=8, decimal_places=3),
]
Eligibility = Literal["lifeline", "protected", "unprotected"]
TariffType = Literal["non_tou", "tou"]
Phase = Literal["single", "three"]


def _lower_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip().lower()
    return value


class TariffSourceView(ApiModel):
    issuing_authority: str
    document_title: str
    source_url: str
    notification_date: date | None = None
    retrieval_date: date
    reference: str
    verification_status: VerificationStatus


class SlabView(ApiModel):
    lower_exclusive_kwh: ExactDecimal
    upper_inclusive_kwh: ExactDecimal | None = None
    rate_per_kwh: ExactDecimal
    fixed_charge_per_kw: ExactDecimal | None = None


class AdjustmentView(ApiModel):
    code: str
    label: str
    state: ComponentState
    required_for_payable: bool
    reason: str


class TariffMetadata(ApiModel):
    """A configuration a caller can inspect. Rates appear only when the file states them."""

    config_id: str
    version: str
    provider_code: str
    consumer_category: str
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    schedule_name: str
    billing_frequency: Literal["monthly"]
    effective_from: date
    effective_to: date | None = None
    slab_method: str
    verification_status: VerificationStatus
    synthetic: bool
    payable_total_available: bool
    slabs: list[SlabView]
    fixed_charge_state: ComponentState
    fixed_charge_basis: str | None = None
    minimum_charge_state: ComponentState
    adjustments: list[AdjustmentView]
    source: TariffSourceView
    limitations: list[str]


class AvailabilityView(ApiModel):
    provider_code: str
    consumer_category: str | None = None
    tariff_type: TariffType | None = None
    eligibility: Eligibility | None = None
    status: Literal["unavailable", "needs_verification"]
    reason: str
    source_url: str | None = None
    retrieval_date: date
    limitations: list[str]


class TariffCatalogResponse(ApiModel):
    configurations: list[TariffMetadata]
    unavailable: list[AvailabilityView]


class TariffResolutionQuery(ApiModel):
    provider_code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=32)
    consumer_category: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=40)
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    billing_date: date

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        updated = dict(value)
        for key in ("consumer_category", "tariff_type", "eligibility"):
            if key in updated:
                updated[key] = _lower_text(updated[key])
        return updated


class TariffResolutionResponse(ApiModel):
    outcome: Literal["matched", "unavailable"]
    reason_code: str
    reason: str
    provider_code: str
    consumer_category: str
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    billing_date: date
    configuration: TariffMetadata | None = None
    missing_inputs: list[str] = Field(default_factory=list)
    limitations: list[str]


class TariffCalculationRequest(ApiModel):
    provider_code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=32)
    consumer_category: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=40)
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    billing_date: date
    consumption_kwh: KilowattHours
    peak_kwh: KilowattHours | None = None
    off_peak_kwh: KilowattHours | None = None
    sanctioned_load_kw: LoadKilowatts | None = None
    maximum_demand_kw: LoadKilowatts | None = None
    phase: Phase | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        updated = dict(value)
        for key in ("consumer_category", "tariff_type", "eligibility", "phase"):
            if key in updated:
                updated[key] = _lower_text(updated[key])
        return updated


class SlabLine(ApiModel):
    label: str
    units: ExactDecimal
    rate_per_kwh: ExactDecimal
    exact_amount: ExactDecimal


class CalculationComponent(ApiModel):
    code: str
    label: str
    state: ComponentState
    amount: MoneyAmount | None = None
    trust_status: TrustStatus
    detail: str = Field(min_length=1)
    lines: list[SlabLine] = Field(default_factory=list)

    @model_validator(mode="after")
    def trust_matches_amount(self) -> "CalculationComponent":
        calculated = self.trust_status == TrustStatus.CALCULATED
        if self.amount is None and calculated:
            raise ValueError("A missing amount cannot be marked Calculated.")
        if self.amount is not None and not calculated:
            raise ValueError("A calculated amount must use the Calculated trust label.")
        return self


class CalculationInputs(ApiModel):
    consumption_kwh: KilowattHours
    peak_kwh: KilowattHours | None = None
    off_peak_kwh: KilowattHours | None = None
    sanctioned_load_kw: LoadKilowatts | None = None
    maximum_demand_kw: LoadKilowatts | None = None
    phase: Phase | None = None


class TariffCalculationResponse(ApiModel):
    outcome: Literal["calculated", "unavailable"]
    trust_status: TrustStatus
    reason_code: str
    reason: str = Field(min_length=1)
    provider_code: str
    consumer_category: str
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    billing_date: date
    config_id: str | None = None
    config_version: str | None = None
    source: TariffSourceView | None = None
    inputs: CalculationInputs
    missing_inputs: list[str]
    blocking_components: list[str]
    components: list[CalculationComponent]
    final_amount: MoneyAmount | None = None
    assumptions: list[str]
    limitations: list[str]

    @model_validator(mode="after")
    def totals_match_the_outcome(self) -> "TariffCalculationResponse":
        if self.outcome == "calculated":
            if self.final_amount is None or self.trust_status != TrustStatus.CALCULATED:
                raise ValueError("A calculated result needs a final amount and the Calculated label.")
            total = sum(
                (component.amount for component in self.components if component.amount is not None),
                start=Decimal("0.00"),
            )
            if total != self.final_amount:
                raise ValueError("The final amount does not equal the component amounts.")
            return self
        if self.final_amount is not None or self.trust_status == TrustStatus.CALCULATED:
            raise ValueError("An unavailable result cannot carry a payable total or the Calculated label.")
        return self
