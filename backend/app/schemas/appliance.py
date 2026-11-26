"""Appliance inputs and scenario results. The API does not keep them."""

import re
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, model_validator

from app.schemas.common import ApiModel, TrustStatus, reject_unsafe_decimal_input

_WHOLE_NUMBER = re.compile(r"[0-9]+")


def reject_unsafe_whole_number(value: object) -> object:
    if isinstance(value, bool):
        raise ValueError("Enter a whole number.")
    if isinstance(value, float):
        raise ValueError("Enter a whole number. Binary floats are not accepted.")
    if isinstance(value, str):
        stripped = value.strip()
        if not _WHOLE_NUMBER.fullmatch(stripped):
            raise ValueError("Enter a whole number without scientific notation.")
        return stripped
    return value


Watts = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(gt=0, le=Decimal("100000"), max_digits=9, decimal_places=3),
]
HoursPerDay = Annotated[
    Decimal,
    BeforeValidator(reject_unsafe_decimal_input),
    Field(gt=0, le=Decimal("24"), max_digits=5, decimal_places=3),
]
Quantity = Annotated[int, BeforeValidator(reject_unsafe_whole_number), Field(gt=0, le=100)]
Days = Annotated[int, BeforeValidator(reject_unsafe_whole_number), Field(gt=0, le=366)]
DaysPerWeek = Annotated[int, BeforeValidator(reject_unsafe_whole_number), Field(ge=1, le=7)]


class ApplianceSpec(ApiModel):
    """A specification the household entered. The wattage is not a verified rating."""

    id: UUID
    name: str = Field(min_length=1, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=40)
    rated_watts: Watts
    quantity: Quantity
    operating_hours_per_day: HoursPerDay
    operating_days_per_week: DaysPerWeek | None = None
    notes: str | None = Field(default=None, max_length=240)


class ConsumptionRequest(ApiModel):
    appliances: list[ApplianceSpec] = Field(default_factory=list, max_length=40)
    days: Days | None = None

    @model_validator(mode="after")
    def ids_are_unique(self) -> "ConsumptionRequest":
        ids = [item.id for item in self.appliances]
        if len(ids) != len(set(ids)):
            raise ValueError("Each appliance id must be unique.")
        return self


class ScenarioRequest(ApiModel):
    baseline: list[ApplianceSpec] = Field(default_factory=list, max_length=40)
    proposed: list[ApplianceSpec] = Field(default_factory=list, max_length=40)
    days: Days

    @model_validator(mode="after")
    def ids_match(self) -> "ScenarioRequest":
        baseline_ids = [item.id for item in self.baseline]
        proposed_ids = [item.id for item in self.proposed]
        if len(baseline_ids) != len(set(baseline_ids)) or len(proposed_ids) != len(set(proposed_ids)):
            raise ValueError("Each appliance id must be unique.")
        if set(baseline_ids) != set(proposed_ids):
            raise ValueError("The scenario must include the same appliances as the baseline.")
        return self


class ApplianceLine(ApiModel):
    id: UUID
    name: str
    input_source: Literal["entered_by_household"] = "entered_by_household"
    rated_watts: str
    quantity: int
    operating_hours_per_day: str
    operating_days_per_week: int | None = None
    daily_kwh: str
    period_kwh: str | None = None
    share_percent: str | None = None
    trust_status: TrustStatus
    detail: str


class PkrImpact(ApiModel):
    value: str | None = None
    trust_status: TrustStatus
    reason: str
    missing_components: list[str]
    comparable: bool = False


class ConsumptionResponse(ApiModel):
    status: Literal["calculated", "unavailable"]
    total_daily_kwh: str | None = None
    total_period_kwh: str | None = None
    days: int | None = None
    appliances: list[ApplianceLine]
    assumptions: list[str]
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class ApplianceChange(ApiModel):
    id: UUID
    name: str
    direction: Literal["reduced", "increased", "unchanged"]
    baseline_kwh: str
    scenario_kwh: str
    difference_kwh: str
    percentage_difference: str | None = None
    trust_status: TrustStatus
    detail: str


class ScenarioResponse(ApiModel):
    status: Literal["estimated", "unavailable"]
    direction: Literal["reduced", "increased", "unchanged", "unavailable"]
    days: int
    baseline_kwh: str | None = None
    scenario_kwh: str | None = None
    difference_kwh: str | None = None
    percentage_difference: str | None = None
    appliances: list[ApplianceChange]
    assumptions: list[str]
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class ActionItem(ApiModel):
    title: str
    appliance_id: UUID
    appliance_name: str
    baseline_assumption: str
    proposed_assumption: str
    difference_kwh: str
    direction: Literal["reduced", "increased"]
    trust_status: TrustStatus
    explanation: str


class ActionPlanResponse(ApiModel):
    status: Literal["estimated", "unavailable"]
    days: int
    actions: list[ActionItem]
    detail: str
    assumptions: list[str]
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"
