"""Memory and spill budget accounting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.errors import MemoryBudgetExceeded


class MemoryUsageSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_in_memory_bytes: int = Field(ge=0)
    current_spill_bytes: int = Field(ge=0)
    peak_in_memory_bytes: int = Field(ge=0)
    peak_spill_bytes: int = Field(ge=0)


@dataclass
class MemoryBudget:
    max_in_memory_fragment_bytes: int
    max_total_in_memory_bytes: int
    spill_dir: Path | None = None
    allow_spill_to_disk: bool = False
    max_spill_bytes: int = 0
    reject_when_over_budget: bool = True
    current_in_memory_bytes: int = 0
    current_spill_bytes: int = 0
    peak_in_memory_bytes: int = 0
    peak_spill_bytes: int = 0

    def can_hold_in_memory(self, payload_bytes: int) -> bool:
        return (
            payload_bytes <= self.max_in_memory_fragment_bytes
            and self.current_in_memory_bytes + payload_bytes <= self.max_total_in_memory_bytes
        )

    def reserve_memory(self, payload_bytes: int) -> None:
        if not self.can_hold_in_memory(payload_bytes):
            raise MemoryBudgetExceeded("payload exceeds in-memory budget")
        self.current_in_memory_bytes += payload_bytes
        self.peak_in_memory_bytes = max(
            self.peak_in_memory_bytes,
            self.current_in_memory_bytes,
        )

    def release_memory(self, payload_bytes: int) -> None:
        self.current_in_memory_bytes = max(self.current_in_memory_bytes - payload_bytes, 0)

    def can_spill(self, payload_bytes: int) -> bool:
        return (
            self.allow_spill_to_disk
            and self.spill_dir is not None
            and self.current_spill_bytes + payload_bytes <= self.max_spill_bytes
        )

    def reserve_spill(self, payload_bytes: int) -> None:
        if not self.can_spill(payload_bytes):
            raise MemoryBudgetExceeded("payload exceeds spill budget")
        self.current_spill_bytes += payload_bytes
        self.peak_spill_bytes = max(self.peak_spill_bytes, self.current_spill_bytes)

    def release_spill(self, payload_bytes: int) -> None:
        self.current_spill_bytes = max(self.current_spill_bytes - payload_bytes, 0)

    def snapshot(self) -> MemoryUsageSnapshot:
        return MemoryUsageSnapshot(
            current_in_memory_bytes=self.current_in_memory_bytes,
            current_spill_bytes=self.current_spill_bytes,
            peak_in_memory_bytes=self.peak_in_memory_bytes,
            peak_spill_bytes=self.peak_spill_bytes,
        )

