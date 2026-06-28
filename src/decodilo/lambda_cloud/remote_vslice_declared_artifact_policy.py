"""Manifest-driven declared artifact capture policy."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    load_lambda_remote_vertical_slice_command_manifest,
)


class LambdaRemoteVSliceDeclaredArtifactPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str
    policy_status: str
    declared_artifact_path: str | None = None
    declared_artifact_paths: list[str] = Field(default_factory=list)
    max_content_bytes: int = 32768
    artifact_type: str = "json"
    capture_on_success: bool = True
    capture_on_failure: bool = True
    secret_scan_required: bool = True
    redact_before_persist: bool = True
    parsed_summary_required_where_possible: bool = True
    raw_content_persist_allowed_if_safe: bool = True
    no_arbitrary_file_reads: bool = True
    reject_undeclared_paths: bool = True
    reject_directories: bool = True
    reject_globs: bool = True
    reject_fallback_paths: bool = True
    reject_relative_traversal: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRemoteVSliceDeclaredArtifactPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("declared artifact policy must remain offline")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("defined declared artifact policy cannot carry blockers")
        if (
            self.declared_artifact_path
            and self.declared_artifact_path not in self.declared_artifact_paths
        ):
            raise ValueError("primary declared artifact path must be in declared paths")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _path_is_safe_remote_tmp_json(path: str) -> bool:
    parsed = PurePosixPath(path)
    text = str(parsed)
    return (
        parsed.is_absolute()
        and text.startswith("/tmp/")
        and parsed.suffix == ".json"
        and ".." not in parsed.parts
        and "*" not in text
        and "?" not in text
        and "[" not in text
        and "]" not in text
    )


def _declared_paths_from_manifest(manifest_path: str | Path) -> tuple[str, list[str], list[str]]:
    manifest = load_lambda_remote_vertical_slice_command_manifest(manifest_path)
    blockers: list[str] = []
    paths: list[str] = []
    for entry in manifest.command_entries:
        tokens = list(entry.argv_tokens)
        for index, token in enumerate(tokens):
            if token == "--out" and index + 1 < len(tokens):
                paths.append(tokens[index + 1])
    unique_paths = sorted(set(paths))
    if not unique_paths:
        blockers.append("manifest_declares_no_output_artifact_path")
    if len(unique_paths) > 1:
        blockers.append("manifest_declares_multiple_output_artifact_paths")
    for path in unique_paths:
        if not _path_is_safe_remote_tmp_json(path):
            blockers.append("declared_artifact_path_not_safe")
    return manifest.milestone, unique_paths, sorted(set(blockers))


def build_lambda_remote_vslice_declared_artifact_policy_from_path(
    *,
    manifest: str | Path,
) -> LambdaRemoteVSliceDeclaredArtifactPolicy:
    milestone, paths, blockers = _declared_paths_from_manifest(manifest)
    return LambdaRemoteVSliceDeclaredArtifactPolicy(
        milestone=milestone,
        policy_status="policy_defined" if not blockers else "blocked",
        declared_artifact_path=paths[0] if len(paths) == 1 else None,
        declared_artifact_paths=paths,
        blockers=blockers,
        warnings=[
            "artifact capture is scoped to manifest-declared JSON output paths only",
        ],
    )


def load_lambda_remote_vslice_declared_artifact_policy(
    path: str | Path,
) -> LambdaRemoteVSliceDeclaredArtifactPolicy:
    return LambdaRemoteVSliceDeclaredArtifactPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_declared_artifact_policy(
    path: str | Path,
    policy: LambdaRemoteVSliceDeclaredArtifactPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
