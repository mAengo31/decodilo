"""Machine-readable report models for local multiprocessing runs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReplayValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    replay_passed: bool
    replay_error: str | None = None
    replay_final_global_version: int | None = None
    replay_useful_tokens_accepted: int | None = None


class ProcessSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    syncer_pid: int
    learner_pids: dict[str, list[int]]
    exit_codes: dict[str, int | None]
    killed_learners: list[str] = Field(default_factory=list)
    restarted_learners: list[str] = Field(default_factory=list)
    slowed_learners: list[str] = Field(default_factory=list)
    restored_learners: list[str] = Field(default_factory=list)
    syncer_restarts: list[int] = Field(default_factory=list)
    unhealthy_learners_observed: list[str] = Field(default_factory=list)
    orphan_cleanup_performed: bool = False


class LocalRuntimeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    mode: str = "local_multiprocess"
    config: dict[str, Any]
    process_summary: ProcessSummary
    final_global_version: int
    final_loss: float
    recovery_source: str | None = None
    trainer_type: str = "numpy_convex"
    trainer_state_kind: str = "flat"
    trainer_config: dict[str, Any] = Field(default_factory=dict)
    trainer_state_bytes_estimate: int | None = None
    trainer_num_parameters: int | None = None
    trainer_final_loss: float | None = None
    trainer_final_eval_loss: float | None = None
    trainer_nonfinite_detected: bool = False
    trainer_checkpoint_paths: list[str] = Field(default_factory=list)
    trainer_contract_status: dict[str, Any] | None = None
    perf_counters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any]
    metric_validation: dict[str, Any]
    replay_validation: ReplayValidationReport
    budget_manifest: dict[str, Any] | None = None
    run_spec_path: str | None = None
    run_spec_sha256: str | None = None
    artifact_manifest_path: str | None = None
    event_log_path: str
    learner_logs: dict[str, str]
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    code_version: str | None = None
