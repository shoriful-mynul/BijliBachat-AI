"""History comparisons. The API does not keep cycles, snapshots, or targets."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import ApiModel, KilowattHours, TrustStatus, UtcTimestamp
from app.schemas.prediction import ConsumptionForecastRequest, TargetKwh

ForecastMethod = Literal["checkpoint-pace-v1"]


class HistoryCheckpoint(ApiModel):
    """A confirmed checkpoint supplied by the caller. An unconfirmed draft is rejected."""

    id: UUID
    register_kwh: KilowattHours
    read_at: UtcTimestamp
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    confirmed: Literal[True]


class StoredCycleRef(ApiModel):
    id: UUID
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    start_checkpoint_id: UUID
    end_checkpoint_id: UUID
    started_at: UtcTimestamp
    ended_at: UtcTimestamp


class CycleValidateRequest(ApiModel):
    cycle_id: UUID
    start_checkpoint_id: UUID
    end_checkpoint_id: UUID
    readings: list[HistoryCheckpoint] = Field(default_factory=list, max_length=200)
    existing_cycles: list[StoredCycleRef] = Field(default_factory=list, max_length=80)
    ignore_cycle_id: UUID | None = None

    @model_validator(mode="after")
    def checkpoint_ids_are_unique(self) -> "CycleValidateRequest":
        ids = [item.id for item in self.readings]
        if len(ids) != len(set(ids)):
            raise ValueError("Each checkpoint id must be unique.")
        return self


class CycleInput(ApiModel):
    id: UUID
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    start_checkpoint_id: UUID
    end_checkpoint_id: UUID
    started_at: UtcTimestamp
    ended_at: UtcTimestamp
    start_register_kwh: KilowattHours
    end_register_kwh: KilowattHours


class CycleCompareRequest(ApiModel):
    earlier: CycleInput
    later: CycleInput


class SnapshotInput(ApiModel):
    id: UUID
    meter_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{4,32}$")
    created_at: UtcTimestamp
    cycle_started_on: date
    cycle_ends_on: date
    cycle_start_register_kwh: KilowattHours
    latest_register_kwh: KilowattHours
    latest_checkpoint_id: UUID
    projected_cycle_kwh: KilowattHours
    reading_ids: list[UUID] = Field(min_length=1, max_length=200)
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    detail: str | None = Field(default=None, max_length=400)
    trust_status: Literal["Estimated"]
    method: ForecastMethod


class ForecastSnapshotRequest(ConsumptionForecastRequest):
    snapshot_id: UUID


class ForecastComparisonRequest(ApiModel):
    snapshot: SnapshotInput
    cycle: CycleInput


class BaselineComparisonRequest(ApiModel):
    cycle: CycleInput
    cycle_id: UUID
    target_kwh: TargetKwh


class InsightRequest(ApiModel):
    cycles: list[CycleInput] = Field(default_factory=list, max_length=80)


class PkrImpact(ApiModel):
    value: str | None = None
    trust_status: TrustStatus
    reason: str
    missing_components: list[str]
    comparable: bool = False


class CycleView(ApiModel):
    id: UUID
    meter_reference: str
    start_checkpoint_id: UUID
    end_checkpoint_id: UUID
    started_at: datetime
    ended_at: datetime
    start_register_kwh: str
    end_register_kwh: str
    actual_kwh: str
    duration_days: str
    average_daily_kwh: str
    trust_status: TrustStatus
    detail: str


class CycleValidateResponse(ApiModel):
    status: Literal["accepted", "rejected", "unavailable"]
    cycle: CycleView | None = None
    detail: str
    assumptions: list[str]
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class CycleCompareResponse(ApiModel):
    status: Literal["calculated", "unavailable"]
    durations_comparable: bool
    duration_warning: str | None = None
    earlier: CycleView | None = None
    later: CycleView | None = None
    usage_difference_kwh: str | None = None
    absolute_difference_kwh: str | None = None
    percentage_difference: str | None = None
    average_daily_difference_kwh: str | None = None
    direction: Literal["reduced", "increased", "unchanged", "unavailable"]
    detail: str
    assumptions: list[str]
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class ForecastSnapshotView(ApiModel):
    id: UUID
    meter_reference: str | None = None
    created_at: datetime
    cycle_started_on: date
    cycle_ends_on: date
    cycle_start_register_kwh: str
    latest_register_kwh: str
    latest_checkpoint_id: UUID
    projected_cycle_kwh: str
    reading_ids: list[UUID]
    assumptions: list[str]
    trust_status: Literal["Estimated"] = "Estimated"
    method: ForecastMethod = "checkpoint-pace-v1"
    detail: str


class ForecastSnapshotResponse(ApiModel):
    status: Literal["estimated", "unavailable"]
    snapshot: ForecastSnapshotView | None = None
    detail: str
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class ForecastComparisonResponse(ApiModel):
    status: Literal["calculated", "unavailable"]
    direction: Literal["higher", "lower", "equal", "unavailable"]
    actual_kwh: str | None = None
    forecast_kwh: str | None = None
    difference_kwh: str | None = None
    absolute_difference_kwh: str | None = None
    percentage_difference: str | None = None
    actual_trust_status: TrustStatus
    forecast_trust_status: TrustStatus
    difference_trust_status: TrustStatus
    detail: str
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class BaselineComparisonResponse(ApiModel):
    status: Literal["calculated", "unavailable"]
    direction: Literal["higher", "lower", "equal", "unavailable"]
    actual_kwh: str | None = None
    target_kwh: str | None = None
    difference_kwh: str | None = None
    absolute_difference_kwh: str | None = None
    percentage_difference: str | None = None
    input_source: Literal["entered_by_household"] = "entered_by_household"
    trust_status: TrustStatus
    detail: str
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"


class InsightItem(ApiModel):
    code: Literal[
        "insufficient",
        "meter_mismatch",
        "decreased",
        "increased",
        "unchanged",
        "duration_warning",
    ]
    title: str
    detail: str
    trust_status: TrustStatus


class InsightResponse(ApiModel):
    status: Literal["calculated", "unavailable"]
    cycle_count: int
    latest_cycle_kwh: str | None = None
    latest_average_daily_kwh: str | None = None
    direction: Literal["reduced", "increased", "unchanged", "unavailable"]
    insights: list[InsightItem]
    assumptions: list[str]
    limitations: list[str]
    pkr_impact: PkrImpact
    storage: Literal["not_retained"] = "not_retained"
