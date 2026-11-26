"""Consumption forecast and household budget contracts.

The API does not keep either one. A payable amount stays null unless a
complete verified tariff can price it.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field

from app.schemas.common import ApiModel, KilowattHours, TrustStatus, UtcTimestamp, reject_unsafe_decimal_input
from app.schemas.meter_api import LedgerReading
from app.schemas.tariff import Eligibility, TariffType

BudgetPkr = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(
        gt=0,
        le=Decimal("1000000"),
        max_digits=10,
        decimal_places=2,
        description="A household monthly budget in PKR. It is not a tariff.",
    ),
]
TargetKwh = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(
        gt=0,
        le=Decimal("100000"),
        max_digits=9,
        decimal_places=3,
        description="A household consumption preference in kWh. It is not a tariff threshold.",
    ),
]


class BudgetValidationRequest(ApiModel):
    monthly_budget_pkr: BudgetPkr | None = None
    monthly_kwh_target: TargetKwh | None = None


class BudgetValidationResponse(ApiModel):
    monthly_budget_pkr: str | None = None
    monthly_kwh_target: str | None = None
    storage: Literal["browser_only"] = "browser_only"
    limitation: str


class QuantityView(ApiModel):
    value: str | None = None
    trust_status: TrustStatus
    detail: str


class ForecastPoint(ApiModel):
    on: date
    kwh: str
    kind: Literal["observed", "estimated"]
    trust_status: TrustStatus
    label: str


class BillCostView(ApiModel):
    value: str | None = None
    trust_status: TrustStatus
    reason: str
    missing_components: list[str]
    comparable_with_budget: bool


class TargetComparisonView(ApiModel):
    status: Literal["estimated", "unavailable"]
    direction: Literal["higher", "lower", "equal", "unavailable"]
    projected_cycle_kwh: str | None = None
    target_kwh: str | None = None
    difference_kwh: str | None = None
    trust_status: TrustStatus
    detail: str


class ConsumptionForecastRequest(ApiModel):
    as_of: UtcTimestamp
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    readings: list[LedgerReading] = Field(default_factory=list, max_length=200)
    cycle_started_on: date | None = None
    cycle_ends_on: date | None = None
    cycle_start_register_kwh: KilowattHours | None = None
    monthly_budget_pkr: BudgetPkr | None = None
    monthly_kwh_target: TargetKwh | None = None
    provider_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
    consumer_category: str | None = Field(default=None, max_length=40)
    tariff_type: TariffType | None = None
    eligibility: Eligibility | None = None
    billing_date: date | None = None


class ConsumptionForecastResponse(ApiModel):
    forecast_status: Literal["estimated", "unavailable"]
    cycle_consumption_kwh: QuantityView
    average_daily_kwh: QuantityView
    projected_additional_kwh: QuantityView
    projected_cycle_kwh: QuantityView
    observation_period: str | None = None
    observation_days: str | None = None
    remaining_days: str | None = None
    billing_cycle_started_on: date | None = None
    billing_cycle_ends_on: date | None = None
    assumptions: list[str]
    missing_inputs: list[str]
    limitations: list[str]
    series: list[ForecastPoint]
    bill_cost: BillCostView
    budget_comparison: BillCostView
    target_comparison: TargetComparisonView
    monthly_budget_pkr: str | None = None
    monthly_kwh_target: str | None = None
    storage: Literal["not_retained"] = "not_retained"
