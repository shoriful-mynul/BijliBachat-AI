"""Bill extraction, confirmation, and audit contracts."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import (
    ApiModel,
    KilowattHours,
    MoneyAmount,
    TrustStatus,
    UtcTimestamp,
)
from app.schemas.tariff import Eligibility, LoadKilowatts, Phase, TariffSourceView, TariffType

FieldConfidence = Literal["readable", "uncertain", "unreadable", "missing"]
ComparisonOutcome = Literal["match", "possible_mismatch", "not_comparable", "unavailable"]
ConfirmationMarker = Literal["user_confirmed"]


class ExtractedField(ApiModel):
    value: str | None = None
    confidence: FieldConfidence
    readable: bool
    note: str | None = Field(default=None, max_length=240)
    trust_status: TrustStatus


class ExtractedCharge(ApiModel):
    label: str = Field(min_length=1, max_length=80)
    value: str | None = None
    confidence: FieldConfidence
    readable: bool
    note: str | None = Field(default=None, max_length=240)
    trust_status: TrustStatus


class BillExtractionDraft(ApiModel):
    """Unconfirmed reading of a bill. The user must submit values separately."""

    confirmed: Literal[False] = False
    media_type: str
    model: str
    provider_code: ExtractedField
    consumer_category: ExtractedField
    tariff_type: ExtractedField
    eligibility: ExtractedField
    billing_date: ExtractedField
    due_date: ExtractedField
    meter_number: ExtractedField
    consumption_kwh: ExtractedField
    peak_kwh: ExtractedField
    off_peak_kwh: ExtractedField
    current_reading_kwh: ExtractedField
    previous_reading_kwh: ExtractedField
    sanctioned_load_kw: ExtractedField
    energy_charge: ExtractedField
    fixed_charge: ExtractedField
    fuel_price_adjustment: ExtractedField
    gst: ExtractedField
    electricity_duty: ExtractedField
    tv_fee: ExtractedField
    arrears: ExtractedField
    total_amount_due: ExtractedField
    other_charges: list[ExtractedCharge] = Field(default_factory=list)
    limitations: list[str]


class ConfirmedOtherCharge(ApiModel):
    label: str = Field(min_length=1, max_length=80)
    amount: MoneyAmount


class ConfirmedBillRequest(ApiModel):
    """Values the person reviewed. A boolean is not accepted as confirmation."""

    confirmation: ConfirmationMarker
    provider_code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
    consumer_category: str = Field(min_length=1, max_length=40)
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    billing_date: date
    consumption_kwh: KilowattHours
    peak_kwh: KilowattHours | None = None
    off_peak_kwh: KilowattHours | None = None
    sanctioned_load_kw: LoadKilowatts | None = None
    maximum_demand_kw: LoadKilowatts | None = None
    phase: Phase | None = None
    energy_charge: MoneyAmount | None = None
    fixed_charge: MoneyAmount | None = None
    fuel_price_adjustment: MoneyAmount | None = None
    gst: MoneyAmount | None = None
    electricity_duty: MoneyAmount | None = None
    tv_fee: MoneyAmount | None = None
    arrears: MoneyAmount | None = None
    total_amount_due: MoneyAmount | None = None
    other_charges: list[ConfirmedOtherCharge] = Field(default_factory=list, max_length=8)


class ComparisonRow(ApiModel):
    code: str
    label: str
    reported_amount: str | None = None
    calculated_amount: str | None = None
    difference: str | None = None
    outcome: ComparisonOutcome
    trust_status: TrustStatus
    explanation: str


class BillAuditReport(ApiModel):
    provider_code: str
    consumer_category: str
    tariff_type: TariffType
    eligibility: Eligibility | None = None
    billing_period: date
    confirmed: ConfirmationMarker
    config_id: str | None = None
    config_version: str | None = None
    source: TariffSourceView | None = None
    comparisons: list[ComparisonRow]
    missing_inputs: list[str]
    blocking_components: list[str]
    limitations: list[str]
    complete_payable_comparison: bool
    overall_trust_status: TrustStatus
    explanation: str
    calculated_at: UtcTimestamp


class ComplaintDraft(ApiModel):
    submitted: Literal[False] = False
    editable: Literal[True] = True
    text: str
