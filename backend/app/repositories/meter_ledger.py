"""Meter checkpoint storage boundary.

The API process does not keep readings. A later repository can replace
`NotRetainedLedger` without changing validation or Cliff Guard maths.
"""

from typing import Protocol
from uuid import UUID

from app.schemas.meter_reading import MeterReading


class MeterLedger(Protocol):
    def add(self, reading: MeterReading) -> None:
        """Retain a confirmed checkpoint, or do nothing when storage is not configured."""

    def list_for(self, household_id: UUID) -> list[MeterReading]:
        """Return retained checkpoints. An empty list means nothing is retained."""


class NotRetainedLedger:
    """Development ledger used by the API. Confirmed readings are not kept."""

    def add(self, reading: MeterReading) -> None:
        return None

    def list_for(self, household_id: UUID) -> list[MeterReading]:
        return []


class ProcessLocalLedger:
    """In-memory stand-in for tests of this boundary. The API does not install it."""

    def __init__(self) -> None:
        self.items: list[MeterReading] = []

    def add(self, reading: MeterReading) -> None:
        self.items.append(reading)

    def list_for(self, household_id: UUID) -> list[MeterReading]:
        return [item for item in self.items if item.household_id == household_id]
