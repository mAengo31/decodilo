"""Canonical run specification for reproducible local runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo import __version__
from decodilo.pricing.provenance import utc_now_iso


class RunSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    mode: str = "local_multiprocess"
    seed: int
    learners: int = Field(gt=0)
    steps: int = Field(gt=0)
    min_quorum: int = Field(gt=0)
    grace_window: int = Field(ge=0)
    max_staleness_versions: int = Field(ge=0)
    vector_dim: int = Field(gt=0)
    num_fragments: int = Field(gt=0)
    local_steps_per_sync: int = Field(gt=0)
    trainer_type: str = "numpy_convex"
    trainer_config: dict[str, Any] = Field(default_factory=dict)
    heartbeat_settings: dict[str, Any] = Field(default_factory=dict)
    update_delivery_settings: dict[str, Any] = Field(default_factory=dict)
    backpressure_settings: dict[str, Any] = Field(default_factory=dict)
    payload_storage_mode: str = "inline"
    checkpoint_storage_mode: str = "inline"
    merge_mode: str = "in_memory"
    global_update_storage_mode: str = "inline"
    chunk_store_root: str | None = None
    artifact_root: str | None = None
    inline_payload_max_bytes: int = 1_000_000
    chunk_size_bytes: int = 1024 * 1024
    require_chunked_for_large_state: bool = False
    tensor_artifact_codec: str = "json_safe"
    fragment_artifact_codec: str = "json_safe"
    checkpoint_artifact_codec: str = "json_safe"
    chaos_plan: dict[str, Any] = Field(default_factory=dict)
    checkpoint_settings: dict[str, Any] = Field(default_factory=dict)
    pricing_manifest: dict[str, Any] | None = None
    code_version: str | None = __version__ or None
    created_at_utc: str | None = None

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.stable_json().encode("utf-8")).hexdigest()


def write_run_spec(path: str | Path, spec: RunSpec) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(spec.stable_json() + "\n", encoding="utf-8")


def load_run_spec(path: str | Path) -> RunSpec:
    return RunSpec.model_validate_json(Path(path).read_text(encoding="utf-8"))


def make_run_spec_from_config(
    config,
    *,
    run_id: str,
    pricing_manifest: dict[str, Any] | None,
) -> RunSpec:
    return RunSpec(
        run_id=run_id,
        seed=config.seed,
        learners=config.learners,
        steps=config.steps,
        min_quorum=config.min_quorum,
        grace_window=config.grace_window,
        max_staleness_versions=config.max_staleness,
        vector_dim=config.vector_dim,
        num_fragments=config.fragments,
        local_steps_per_sync=config.local_steps_per_sync,
        trainer_type=config.trainer_type,
        trainer_config={
            "learner_lr": config.learner_lr,
            "outer_lr": config.outer_lr,
            **(config.trainer_config or {}),
        },
        heartbeat_settings={
            "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
            "heartbeat_timeout_seconds": config.heartbeat_timeout_seconds,
        },
        update_delivery_settings={
            "update_long_poll_timeout_seconds": config.update_long_poll_timeout_seconds,
        },
        backpressure_settings={
            "max_pending_messages_per_learner": config.max_pending_messages_per_learner,
            "max_pending_fragments_per_learner": config.max_pending_fragments_per_learner,
            "max_inflight_bytes_per_learner": config.max_inflight_bytes_per_learner,
            "max_total_inflight_bytes": config.max_total_inflight_bytes,
            "memory_budget_mb": config.memory_budget_mb,
            "allow_spill_to_disk": config.allow_spill_to_disk,
            "spill_dir": str(config.spill_dir) if config.spill_dir else None,
            "max_spill_mb": config.max_spill_mb,
        },
        payload_storage_mode=config.payload_storage_mode,
        checkpoint_storage_mode=config.checkpoint_storage_mode,
        merge_mode=config.merge_mode,
        global_update_storage_mode=config.global_update_storage_mode,
        chunk_store_root=str(config.chunk_store_root) if config.chunk_store_root else None,
        artifact_root=str(config.artifact_root) if config.artifact_root else None,
        inline_payload_max_bytes=config.inline_payload_max_bytes,
        chunk_size_bytes=config.chunk_size_bytes,
        require_chunked_for_large_state=config.require_chunked_for_large_state,
        tensor_artifact_codec=config.tensor_artifact_codec,
        fragment_artifact_codec=config.fragment_artifact_codec,
        checkpoint_artifact_codec=config.checkpoint_artifact_codec,
        chaos_plan={
            "kill_learner": config.kill_learner.__dict__ if config.kill_learner else None,
            "restart_learner": (
                config.restart_learner.__dict__ if config.restart_learner else None
            ),
            "slow_learner": config.slow_learner.__dict__ if config.slow_learner else None,
            "restore_learner": (
                config.restore_learner.__dict__ if config.restore_learner else None
            ),
            "restart_syncer_after_round": config.restart_syncer_after_round,
        },
        checkpoint_settings={
            "syncer_checkpoint_interval_rounds": config.syncer_checkpoint_interval_rounds,
            "chunked_checkpoints": config.chunked_checkpoints,
            "checkpoint_storage_mode": config.checkpoint_storage_mode,
        },
        pricing_manifest=pricing_manifest,
        created_at_utc=utc_now_iso(),
    )
