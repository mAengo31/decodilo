"""Spill-to-disk policy and helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.memory_budget import MemoryBudget


class SpillPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    allow_spill_to_disk: bool = False
    spill_dir: str | None = None
    max_spill_bytes: int = Field(default=0, ge=0)
    retain_spill_files: bool = False


class SpillDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    should_spill: bool
    reason: str


class SpillManager:
    """Writes oversized payloads into a chunk store under a spill directory."""

    def __init__(self, *, budget: MemoryBudget, run_id: str) -> None:
        self.budget = budget
        self.run_id = run_id
        if budget.spill_dir is None:
            raise ValueError("spill_dir is required for SpillManager")
        self.spill_dir = Path(budget.spill_dir)
        self.store = ChunkStore(self.spill_dir)
        self.manifest_paths: list[Path] = []

    def decide(self, payload_bytes: int) -> SpillDecision:
        if self.budget.can_hold_in_memory(payload_bytes):
            return SpillDecision(should_spill=False, reason="fits_memory")
        if self.budget.can_spill(payload_bytes):
            return SpillDecision(should_spill=True, reason="spill_allowed")
        return SpillDecision(should_spill=False, reason="spill_not_allowed")

    def spill_bytes(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        data: bytes,
        chunk_size_bytes: int = 1024 * 1024,
        metadata: dict | None = None,
    ):
        self.budget.reserve_spill(len(data))
        manifest_path = self.spill_dir / "manifests" / f"{artifact_id}.json"
        manifest = write_binary_artifact(
            store=self.store,
            data=data,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            run_id=self.run_id,
            chunk_size_bytes=chunk_size_bytes,
            metadata=metadata,
            manifest_path=manifest_path,
        )
        self.manifest_paths.append(manifest_path)
        return manifest

    def read_spill(self, manifest) -> bytes:
        return self.store.read_bytes(manifest)

    def cleanup(self, *, retain: bool = False) -> None:
        if retain:
            return
        shutil.rmtree(self.spill_dir, ignore_errors=True)

