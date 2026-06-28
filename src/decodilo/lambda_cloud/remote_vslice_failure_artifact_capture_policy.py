"""Capture-on-failure policy for predeclared remote vertical-slice artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    load_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.runtime_smoke_failure_evidence_policy import (
    load_lambda_runtime_smoke_failure_evidence_policy,
)


class LambdaRemoteVSliceFailureArtifactCapturePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    policy_passed: bool
    capture_on_failure_allowed: bool
    capture_scope: str = "predeclared_artifact_only"
    expected_output_artifact_path: str
    max_artifact_bytes: int
    artifact_type: str = "json"
    no_arbitrary_file_read: bool = True
    no_unbounded_transfer: bool = True
    no_directory_traversal: bool = True
    secret_scan_required: bool = True
    capture_after_failure_is_not_retry: bool = True
    capture_after_failure_is_not_experiment_command: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRemoteVSliceFailureArtifactCapturePolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("failure artifact capture policy must remain offline")
        if self.policy_passed and self.blockers:
            raise ValueError("passing capture policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vslice_failure_artifact_capture_policy_from_paths(
    *,
    expected_artifact_policy: str | Path,
    failure_evidence_policy: str | Path,
) -> LambdaRemoteVSliceFailureArtifactCapturePolicy:
    expected = load_lambda_remote_vslice_expected_artifact_policy(
        expected_artifact_policy
    )
    failure = load_lambda_runtime_smoke_failure_evidence_policy(
        failure_evidence_policy
    )
    blockers: list[str] = []
    if expected.policy_status != "policy_defined":
        blockers.extend(expected.blockers or ["expected_artifact_policy_not_defined"])
    if failure.policy_status != "policy_defined":
        blockers.extend(failure.blockers or ["failure_evidence_policy_not_defined"])
    if expected.expected_output_artifact_path != failure.predeclared_artifact_path:
        blockers.append("artifact_path_policy_mismatch")
    if not expected.capture_allowed_on_failure:
        blockers.append("expected_policy_does_not_allow_failure_capture")
    if not failure.capture_after_nonzero_exit_allowed:
        blockers.append("failure_policy_does_not_allow_nonzero_capture")
    return LambdaRemoteVSliceFailureArtifactCapturePolicy(
        policy_passed=not blockers,
        capture_on_failure_allowed=not blockers,
        expected_output_artifact_path=expected.expected_output_artifact_path,
        max_artifact_bytes=min(expected.max_artifact_bytes, failure.max_artifact_bytes),
        blockers=sorted(set(blockers)),
        warnings=[
            "capture after failure is scoped to the manifest-declared artifact path",
        ],
    )


def load_lambda_remote_vslice_failure_artifact_capture_policy(
    path: str | Path,
) -> LambdaRemoteVSliceFailureArtifactCapturePolicy:
    return LambdaRemoteVSliceFailureArtifactCapturePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_failure_artifact_capture_policy(
    path: str | Path,
    policy: LambdaRemoteVSliceFailureArtifactCapturePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
