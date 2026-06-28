"""Learner/syncer declared artifact policy checks."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    load_lambda_remote_vslice_declared_artifact_policy,
)


class LambdaLearnerSyncerArtifactPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M079S"
    policy_status: str
    declared_artifact_path: str | None = None
    content_capture_allowed: bool
    max_content_bytes: int = 32768
    artifact_type: str = "json"
    capture_on_success: bool = True
    capture_on_failure: bool = True
    no_arbitrary_file_reads: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaLearnerSyncerArtifactPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("learner/syncer artifact policy must remain offline")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("defined learner/syncer artifact policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_learner_syncer_artifact_policy_from_path(
    *,
    declared_artifact_policy: str | Path,
) -> LambdaLearnerSyncerArtifactPolicy:
    policy = load_lambda_remote_vslice_declared_artifact_policy(declared_artifact_policy)
    blockers: list[str] = []
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["declared_artifact_policy_not_defined"])
    if policy.declared_artifact_path != LEARNER_SYNCER_DECLARED_ARTIFACT_PATH:
        blockers.append("learner_syncer_declared_artifact_path_missing")
    return LambdaLearnerSyncerArtifactPolicy(
        policy_status="policy_defined" if not blockers else "blocked",
        declared_artifact_path=policy.declared_artifact_path,
        content_capture_allowed=not blockers,
        max_content_bytes=policy.max_content_bytes,
        artifact_type=policy.artifact_type,
        capture_on_success=policy.capture_on_success,
        capture_on_failure=policy.capture_on_failure,
        no_arbitrary_file_reads=policy.no_arbitrary_file_reads,
        blockers=sorted(set(blockers)),
        warnings=["learner/syncer artifact capture is manifest-declared only"],
    )


def load_lambda_learner_syncer_artifact_policy(
    path: str | Path,
) -> LambdaLearnerSyncerArtifactPolicy:
    return LambdaLearnerSyncerArtifactPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_learner_syncer_artifact_policy(
    path: str | Path,
    policy: LambdaLearnerSyncerArtifactPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
