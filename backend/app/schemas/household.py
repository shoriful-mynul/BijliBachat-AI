"""Household profile contract. This does not persist a household or assign a tariff."""

from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import ApiModel, UtcTimestamp


class HouseholdProfile(ApiModel):
    """A household the product can refer to later.

    There is no address, national ID, or meter account number.
    The provider code is an open label, not a fixed list of companies.
    Protected-consumer status is not a field on this contract.
    """

    id: UUID
    display_name: str = Field(min_length=1, max_length=80)
    provider_code: str = Field(
        min_length=1,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
        description="Distribution company code supplied with the household. Any later company can use its own code.",
    )
    service_region: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="City or service area, when the household supplies one. Not a street address.",
    )
    created_at: UtcTimestamp
    updated_at: UtcTimestamp

    @model_validator(mode="after")
    def updated_at_follows_created_at(self) -> "HouseholdProfile":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be the same moment as created_at or later.")
        return self
