"""Requirements model for a future remote artifact backend.

This module is planning-only. It does not implement or enable any remote
storage backend.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.scaling.scaling_report import LearnerScalingDecisionReport


class RemoteBackendThroughputRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    peak_artifact_read_gbps: float = Field(ge=0)
    peak_artifact_write_gbps: float = Field(ge=0)
    peak_artifact_ops_per_second: float = Field(ge=0)
    peak_syncer_merge_gbps: float = Field(ge=0)


class RemoteBackendLatencyRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_put_latency_ms: float | None = Field(default=None, gt=0)
    max_get_latency_ms: float | None = Field(default=None, gt=0)
    max_list_latency_ms: float | None = Field(default=None, gt=0)


class RemoteBackendConsistencyRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_read_after_write_consistency: bool = True
    required_monotonic_manifest_visibility: bool = True
    required_atomic_manifest_commit: bool = True
    required_conditional_put: bool = True


class RemoteBackendIntegrityRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_content_hash_validation: bool = True
    required_idempotent_put: bool = True
    required_idempotent_delete: bool = True


class RemoteBackendSecurityRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_encryption_at_rest: bool = True
    required_encryption_in_transit: bool = True
    required_authentication: bool = True
    required_authorization_scopes: list[str] = Field(
        default_factory=lambda: ["learner-artifact-write", "syncer-artifact-read"]
    )


class RemoteBackendLifecycleRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_lifecycle_delete: bool = True
    required_retention_policy: bool = True
    required_transaction_log: bool = True


class RemoteBackendCostRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_monthly_storage_cost: float | None = Field(default=None, ge=0)
    max_artifact_egress_cost: float | None = Field(default=None, ge=0)


class RemoteBackendReplayRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_replay_snapshot_frequency: str
    event_log_growth_mb_per_hour: float = Field(ge=0)


class RemoteBackendCheckpointRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    checkpoint_storage_growth_gb_per_hour: float = Field(ge=0)


class RemoteBackendRequirementSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_schema_version: int = 1
    scenario_id: str
    source_scaling_report_id: str | None = None
    target_learner_count: int = Field(gt=0)
    stress_learner_count: int = Field(gt=0)
    peak_artifact_read_gbps: float = Field(ge=0)
    peak_artifact_write_gbps: float = Field(ge=0)
    peak_artifact_ops_per_second: float = Field(ge=0)
    peak_syncer_merge_gbps: float = Field(ge=0)
    checkpoint_storage_growth_gb_per_hour: float = Field(ge=0)
    event_log_growth_mb_per_hour: float = Field(ge=0)
    required_replay_snapshot_frequency: str
    max_put_latency_ms: float | None = Field(default=None, gt=0)
    max_get_latency_ms: float | None = Field(default=None, gt=0)
    max_list_latency_ms: float | None = Field(default=None, gt=0)
    required_read_after_write_consistency: bool = True
    required_monotonic_manifest_visibility: bool = True
    required_atomic_manifest_commit: bool = True
    required_conditional_put: bool = True
    required_content_hash_validation: bool = True
    required_encryption_at_rest: bool = True
    required_encryption_in_transit: bool = True
    required_authentication: bool = True
    required_authorization_scopes: list[str] = Field(
        default_factory=lambda: ["learner-artifact-write", "syncer-artifact-read"]
    )
    required_idempotent_put: bool = True
    required_idempotent_delete: bool = True
    required_lifecycle_delete: bool = True
    required_retention_policy: bool = True
    required_transaction_log: bool = True
    max_monthly_storage_cost: float | None = Field(default=None, ge=0)
    max_artifact_egress_cost: float | None = Field(default=None, ge=0)
    notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_critical_requirements(self) -> RemoteBackendRequirementSet:
        if self.stress_learner_count < self.target_learner_count:
            raise ValueError("stress_learner_count must be >= target_learner_count")
        if not self.required_replay_snapshot_frequency:
            raise ValueError("required_replay_snapshot_frequency is required")
        if self.required_authentication and not self.required_authorization_scopes:
            raise ValueError("authorization scopes are required when authentication is required")
        return self

    @property
    def throughput(self) -> RemoteBackendThroughputRequirement:
        return RemoteBackendThroughputRequirement(
            peak_artifact_read_gbps=self.peak_artifact_read_gbps,
            peak_artifact_write_gbps=self.peak_artifact_write_gbps,
            peak_artifact_ops_per_second=self.peak_artifact_ops_per_second,
            peak_syncer_merge_gbps=self.peak_syncer_merge_gbps,
        )

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def requirements_from_scaling_report(
    report: LearnerScalingDecisionReport,
    *,
    stress_multiplier: float = 2.0,
) -> RemoteBackendRequirementSet:
    targets = report.backend_design_targets
    target_count = int(targets["target_learner_count"])
    return RemoteBackendRequirementSet(
        scenario_id=str(report.scenario.get("scenario_id", "learner-scaling")),
        source_scaling_report_id=str(report.scenario.get("scenario_id", "")) or None,
        target_learner_count=target_count,
        stress_learner_count=max(target_count, int(round(target_count * stress_multiplier))),
        peak_artifact_read_gbps=float(targets["peak_artifact_read_gbps"]),
        peak_artifact_write_gbps=float(targets["peak_artifact_write_gbps"]),
        peak_artifact_ops_per_second=float(targets["peak_artifact_ops_per_second"]),
        peak_syncer_merge_gbps=float(targets["peak_syncer_merge_gbps"]),
        checkpoint_storage_growth_gb_per_hour=float(
            targets["checkpoint_storage_growth_gb_per_hour"]
        ),
        event_log_growth_mb_per_hour=float(targets["event_log_growth_mb_per_hour"]),
        required_replay_snapshot_frequency=str(
            targets["required_replay_snapshot_frequency"]
        ),
        limitations=[
            "derived from local learner-scaling planning",
            "does not validate a real remote backend",
        ],
    )


def load_remote_backend_requirements(path: str | Path) -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_requirements(
    path: str | Path,
    requirements: RemoteBackendRequirementSet,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(requirements.to_json(), encoding="utf-8")

