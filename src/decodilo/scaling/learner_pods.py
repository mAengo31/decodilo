"""Typed learner-pod scaling inputs for planning-only estimates."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LearnerPodShape(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape_id: str
    learner_count: int = Field(gt=0)
    gpus_per_learner: float = Field(ge=0)
    total_gpus: float = Field(gt=0)
    gpu_type: str | None = None
    per_gpu_token_rate: float | None = Field(default=None, ge=0)
    per_learner_token_rate: float = Field(gt=0)
    learner_mfu_estimate: float | None = Field(default=None, ge=0)
    learner_memory_gb: float | None = Field(default=None, ge=0)
    learner_failure_rate_per_hour: float = Field(ge=0)
    learner_recovery_time_seconds: float = Field(ge=0)
    learner_preemption_rate_per_hour: float | None = Field(default=None, ge=0)
    learner_startup_time_seconds: float | None = Field(default=None, ge=0)
    learner_price_per_hour: float | None = Field(default=None, ge=0)
    heterogeneity_group: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_total_gpus(self) -> LearnerPodShape:
        expected = self.learner_count * self.gpus_per_learner
        if self.gpus_per_learner > 0 and abs(expected - self.total_gpus) > 1e-9:
            raise ValueError("total_gpus must equal learner_count * gpus_per_learner")
        return self

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


class LearnerPodPool(BaseModel):
    model_config = ConfigDict(frozen=True)

    shapes: list[LearnerPodShape]

    @model_validator(mode="after")
    def _validate_shapes(self) -> LearnerPodPool:
        if not self.shapes:
            raise ValueError("at least one learner pod shape is required")
        ids = [shape.shape_id for shape in self.shapes]
        if len(set(ids)) != len(ids):
            raise ValueError("learner pod shape_id values must be unique")
        return self


class LearnerPodCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int = Field(gt=0)
    total_gpus: float = Field(gt=0)
    gpus_per_learner: float = Field(ge=0)
    per_learner_token_rate: float = Field(gt=0)
    learner_price_per_hour: float | None = Field(default=None, ge=0)
    heterogeneity_group: str | None = None
    notes: list[str] = Field(default_factory=list)


class LearnerPodScalingScenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str
    mode: Literal["fixed_total_compute", "expanding_compute", "scavenged_compute"]
    candidate_learner_counts: list[int]
    fixed_total_gpus: float | None = Field(default=None, gt=0)
    gpus_per_learner: float | None = Field(default=None, gt=0)
    total_gpus_by_candidate: dict[int, float] | None = None
    training_duration_hours: float = Field(gt=0)
    target_useful_tokens: float | None = Field(default=None, gt=0)
    model_parameter_count: int | None = Field(default=None, gt=0)
    bytes_per_parameter: float | None = Field(default=None, gt=0)
    fragment_count: int = Field(gt=0)
    chunk_size_bytes: int = Field(gt=0)
    sync_interval_steps: int = Field(gt=0)
    local_step_seconds: float = Field(gt=0)
    min_quorum_policy: dict[str, Any] = Field(default_factory=dict)
    grace_window_policy: dict[str, Any] = Field(default_factory=dict)
    bandwidth_cap_gbps: float | None = Field(default=None, gt=0)
    artifact_backend_read_gbps: float | None = Field(default=None, gt=0)
    artifact_backend_write_gbps: float | None = Field(default=None, gt=0)
    syncer_max_merge_gbps: float | None = Field(default=None, gt=0)
    price_snapshot_ref: str | None = None
    overhead_report_refs: list[str] = Field(default_factory=list)
    calibration_profile: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_scenario(self) -> LearnerPodScalingScenario:
        if not self.candidate_learner_counts:
            raise ValueError("candidate_learner_counts must not be empty")
        if any(count <= 0 for count in self.candidate_learner_counts):
            raise ValueError("candidate learner counts must be positive")
        if self.mode == "fixed_total_compute" and self.fixed_total_gpus is None:
            raise ValueError("fixed_total_compute requires fixed_total_gpus")
        if self.mode == "expanding_compute" and self.gpus_per_learner is None:
            raise ValueError("expanding_compute requires gpus_per_learner")
        if self.total_gpus_by_candidate is not None:
            missing = set(self.candidate_learner_counts) - set(self.total_gpus_by_candidate)
            if missing:
                raise ValueError(f"total_gpus_by_candidate missing candidates: {sorted(missing)}")
            if any(total <= 0 for total in self.total_gpus_by_candidate.values()):
                raise ValueError("total_gpus_by_candidate values must be positive")
        quorum = self.min_quorum_policy.get("fixed")
        if quorum is not None:
            max_learners = max(self.candidate_learner_counts)
            if int(quorum) <= 0 or int(quorum) > max_learners:
                raise ValueError("fixed quorum must be in [1, max candidate learners]")
        if (self.model_parameter_count is None) != (self.bytes_per_parameter is None):
            raise ValueError(
                "model_parameter_count and bytes_per_parameter must be provided together"
            )
        return self

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def total_gpus_for(self, learner_count: int) -> float:
        if learner_count not in self.candidate_learner_counts:
            raise ValueError("learner_count is not in scenario candidates")
        if self.total_gpus_by_candidate is not None:
            return float(self.total_gpus_by_candidate[learner_count])
        if self.mode == "fixed_total_compute":
            return float(self.fixed_total_gpus or 0)
        return float(learner_count * (self.gpus_per_learner or 1.0))

    def min_quorum_for(self, learner_count: int) -> int:
        if "fixed" in self.min_quorum_policy:
            quorum = int(self.min_quorum_policy["fixed"])
        else:
            ratio = float(self.min_quorum_policy.get("ratio", 0.5))
            quorum = max(1, int(round(learner_count * ratio)))
        if quorum > learner_count:
            raise ValueError("quorum cannot exceed learner_count")
        return quorum

    def grace_window_seconds_for(self, learner_count: int) -> float:
        _ = learner_count
        return float(self.grace_window_policy.get("seconds", 0.0))


def load_learner_scaling_scenario(path: str) -> LearnerPodScalingScenario:
    from pathlib import Path

    return LearnerPodScalingScenario.model_validate_json(Path(path).read_text(encoding="utf-8"))
