"""Runtime resource-limit models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.memory_budget import MemoryBudget


class RuntimeResourceLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_in_memory_fragment_bytes: int = Field(default=128 * 1024 * 1024, gt=0)
    max_total_in_memory_bytes: int = Field(default=512 * 1024 * 1024, gt=0)
    spill_dir: str | None = None
    allow_spill_to_disk: bool = False
    max_spill_bytes: int = Field(default=0, ge=0)
    reject_when_over_budget: bool = True
    chunked_checkpoints: bool = False

    @classmethod
    def from_mb(
        cls,
        *,
        memory_budget_mb: int | None,
        spill_dir: str | Path | None = None,
        allow_spill_to_disk: bool = False,
        max_spill_mb: int | None = None,
        chunked_checkpoints: bool = False,
    ) -> RuntimeResourceLimits:
        budget_bytes = (
            128 * 1024 * 1024
            if memory_budget_mb is None
            else int(memory_budget_mb) * 1024 * 1024
        )
        return cls(
            max_in_memory_fragment_bytes=budget_bytes,
            max_total_in_memory_bytes=budget_bytes,
            spill_dir=str(spill_dir) if spill_dir is not None else None,
            allow_spill_to_disk=allow_spill_to_disk,
            max_spill_bytes=(max_spill_mb or 0) * 1024 * 1024,
            chunked_checkpoints=chunked_checkpoints,
        )

    def to_memory_budget(self) -> MemoryBudget:
        return MemoryBudget(
            max_in_memory_fragment_bytes=self.max_in_memory_fragment_bytes,
            max_total_in_memory_bytes=self.max_total_in_memory_bytes,
            spill_dir=Path(self.spill_dir) if self.spill_dir is not None else None,
            allow_spill_to_disk=self.allow_spill_to_disk,
            max_spill_bytes=self.max_spill_bytes,
            reject_when_over_budget=self.reject_when_over_budget,
        )
