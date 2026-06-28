"""Policy for persisting declared runtime-smoke artifact bodies safely."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    load_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    DEFAULT_MAX_CONTENT_BYTES,
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


class LambdaRuntimeSmokeArtifactBodyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075T"
    policy_status: str
    declared_artifact_path: str = RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    content_capture_allowed: bool
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES
    artifact_type: str = "json"
    capture_on_success: bool = True
    capture_on_failure: bool = True
    secret_scan_required: bool = True
    redact_before_persist: bool = True
    parsed_summary_required: bool = True
    raw_content_persist_allowed: bool
    raw_content_requires_size_within_limit: bool = True
    raw_content_requires_json_parse_success: bool = True
    raw_content_requires_secret_scan_pass: bool = True
    no_arbitrary_file_reads: bool = True
    no_directory_reads: bool = True
    no_globbing: bool = True
    no_fallback_paths: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRuntimeSmokeArtifactBodyPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("artifact body policy must remain offline")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("defined artifact body policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_runtime_smoke_artifact_body_policy_from_path(
    *,
    expected_artifact_policy: str | Path,
) -> LambdaRuntimeSmokeArtifactBodyPolicy:
    expected = load_lambda_remote_vslice_expected_artifact_policy(
        expected_artifact_policy
    )
    blockers: list[str] = []
    if expected.policy_status != "policy_defined":
        blockers.extend(expected.blockers or ["expected_artifact_policy_not_defined"])
    if expected.expected_output_artifact_path != RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH:
        blockers.append("declared_artifact_path_mismatch")
    if expected.artifact_type != "json":
        blockers.append("expected_artifact_type_must_be_json")
    if not expected.capture_allowed_on_success:
        blockers.append("capture_on_success_required")
    if not expected.capture_allowed_on_failure:
        blockers.append("capture_on_failure_required")
    max_bytes = min(expected.max_artifact_bytes, DEFAULT_MAX_CONTENT_BYTES)
    return LambdaRuntimeSmokeArtifactBodyPolicy(
        policy_status="policy_defined" if not blockers else "blocked",
        content_capture_allowed=not blockers,
        max_content_bytes=max_bytes,
        raw_content_persist_allowed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=[
            (
                "raw runtime-smoke artifact bodies may be persisted only when bounded, "
                "JSON, and secret-scan clean"
            ),
            "otherwise only a redacted parsed summary may be persisted",
        ],
    )


def load_lambda_runtime_smoke_artifact_body_policy(
    path: str | Path,
) -> LambdaRuntimeSmokeArtifactBodyPolicy:
    return LambdaRuntimeSmokeArtifactBodyPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_artifact_body_policy(
    path: str | Path,
    policy: LambdaRuntimeSmokeArtifactBodyPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
