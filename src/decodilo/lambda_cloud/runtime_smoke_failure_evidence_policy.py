"""Policy for collecting bounded evidence after runtime-smoke failure."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vertical_slice_policy import M075R_OUTPUT_ARTIFACT_PATH


class LambdaRuntimeSmokeFailureEvidencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    policy_status: str = "policy_defined"
    command_must_write_report_on_failure: bool = True
    capture_after_nonzero_exit_allowed: bool = True
    predeclared_artifact_path: str = M075R_OUTPUT_ARTIFACT_PATH
    max_artifact_bytes: int = 32768
    artifact_type: str = "json"
    metadata_hash_required: bool = True
    secret_scan_required: bool = True
    capture_after_failure_is_not_retry: bool = True
    capture_after_failure_is_not_experiment_command: bool = True
    no_arbitrary_file_reads: bool = True
    no_directory_traversal: bool = True
    no_extra_file_transfer_except_predeclared_artifact: bool = True
    artifact_absent_is_recorded_then_terminate: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRuntimeSmokeFailureEvidencePolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("failure evidence policy must remain offline")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("defined failure evidence policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_runtime_smoke_failure_evidence_policy() -> (
    LambdaRuntimeSmokeFailureEvidencePolicy
):
    return LambdaRuntimeSmokeFailureEvidencePolicy(
        warnings=[
            "capture is limited to the manifest-declared runtime-smoke output artifact",
        ],
    )


def load_lambda_runtime_smoke_failure_evidence_policy(
    path: str | Path,
) -> LambdaRuntimeSmokeFailureEvidencePolicy:
    return LambdaRuntimeSmokeFailureEvidencePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_failure_evidence_policy(
    path: str | Path,
    policy: LambdaRuntimeSmokeFailureEvidencePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
