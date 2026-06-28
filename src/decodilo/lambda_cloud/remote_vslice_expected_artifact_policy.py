"""Expected output artifact policy for remote vertical-slice commands."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    M075R_OUTPUT_ARTIFACT_PATH,
    load_lambda_remote_vertical_slice_command_manifest,
)


class LambdaRemoteVSliceExpectedArtifactPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    policy_status: str
    expected_output_artifact_path: str = M075R_OUTPUT_ARTIFACT_PATH
    max_artifact_bytes: int = 32768
    artifact_type: str = "json"
    capture_allowed_on_success: bool = True
    capture_allowed_on_failure: bool = True
    capture_must_be_bounded: bool = True
    secret_scan_or_redaction_required: bool = True
    metadata_always_captured_when_feasible: bool = True
    raw_content_capture_optional_if_clean_and_bounded: bool = True
    no_arbitrary_file_reads: bool = True
    no_directory_traversal: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRemoteVSliceExpectedArtifactPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("expected artifact policy must remain offline")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("defined expected artifact policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _has_declared_output_path(argv_tokens: list[str], expected_path: str) -> bool:
    return any(
        token == "--out"
        and index + 1 < len(argv_tokens)
        and argv_tokens[index + 1] == expected_path
        for index, token in enumerate(argv_tokens)
    )


def _path_is_safe_remote_tmp_json(path: str) -> bool:
    parsed = PurePosixPath(path)
    return (
        path == M075R_OUTPUT_ARTIFACT_PATH
        and parsed.is_absolute()
        and ".." not in parsed.parts
        and str(parsed).startswith("/tmp/")
        and parsed.suffix == ".json"
    )


def build_lambda_remote_vslice_expected_artifact_policy_from_path(
    *,
    manifest: str | Path,
) -> LambdaRemoteVSliceExpectedArtifactPolicy:
    command_manifest = load_lambda_remote_vertical_slice_command_manifest(manifest)
    blockers: list[str] = []
    runtime_entries = [
        entry
        for entry in command_manifest.command_entries
        if entry.stage == "runtime_smoke_command"
    ]
    if command_manifest.milestone != "M075R":
        blockers.append("m075r_manifest_required")
    if len(runtime_entries) != 1:
        blockers.append("exactly_one_runtime_smoke_command_required")
    elif not _has_declared_output_path(
        list(runtime_entries[0].argv_tokens),
        M075R_OUTPUT_ARTIFACT_PATH,
    ):
        blockers.append("runtime_smoke_declared_output_path_missing")
    if not _path_is_safe_remote_tmp_json(M075R_OUTPUT_ARTIFACT_PATH):
        blockers.append("expected_artifact_path_not_safe")
    return LambdaRemoteVSliceExpectedArtifactPolicy(
        policy_status="policy_defined" if not blockers else "blocked",
        blockers=blockers,
        warnings=[
            "expected artifact capture is scoped to the declared M075R JSON report",
        ],
    )


def load_lambda_remote_vslice_expected_artifact_policy(
    path: str | Path,
) -> LambdaRemoteVSliceExpectedArtifactPolicy:
    return LambdaRemoteVSliceExpectedArtifactPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_expected_artifact_policy(
    path: str | Path,
    policy: LambdaRemoteVSliceExpectedArtifactPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
