"""Manifest-driven artifact policy and capture helpers for remote vertical slices."""

from __future__ import annotations

import json
import shlex
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_parser import (
    BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH,
    parse_bounded_diloco_experiment_artifact_file,
)
from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_diloco_artifact_file,
)
from decodilo.lambda_cloud.diloco_optimizer_artifact_parser import (
    DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_diloco_optimizer_artifact_file,
)
from decodilo.lambda_cloud.integrated_diloco_artifact_parser import (
    INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_integrated_diloco_artifact_file,
)
from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.parameter_fragment_artifact_parser import (
    PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_parameter_fragment_artifact_file,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_capture import (
    LambdaRemoteVSliceDeclaredArtifactCapture,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    DEFAULT_MAX_CONTENT_BYTES,
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_runtime_smoke_artifact_file,
)
from decodilo.lambda_cloud.tiny_real_training_artifact_parser import (
    TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_tiny_real_training_artifact_file,
)

SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-synthetic-experiment.json"
)

SUPPORTED_MANIFEST_ARTIFACT_PATHS = {
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
    SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH,
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH,
    INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH,
    BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH,
    TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH,
}


class LambdaRemoteVSliceManifestArtifactPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str
    policy_status: str
    declared_artifact_path: str | None = None
    declared_artifact_paths: list[str] = Field(default_factory=list)
    supported_declared_paths: list[str] = Field(
        default_factory=lambda: sorted(SUPPORTED_MANIFEST_ARTIFACT_PATHS)
    )
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES
    artifact_type: str = "json"
    capture_on_success: bool = True
    capture_on_failure: bool = True
    secret_scan_required: bool = True
    redact_before_persist: bool = True
    parsed_summary_required_where_possible: bool = True
    raw_content_persist_allowed_if_safe: bool = True
    accept_only_manifest_declared_paths: bool = True
    no_arbitrary_file_reads: bool = True
    reject_undeclared_paths: bool = True
    reject_directories: bool = True
    reject_globs: bool = True
    reject_fallback_paths: bool = True
    reject_relative_paths: bool = True
    reject_traversal: bool = True
    reject_symlink_escapes: bool = True
    runtime_smoke_declared_artifact_supported: bool = False
    synthetic_experiment_declared_artifact_supported: bool = False
    learner_syncer_declared_artifact_supported: bool = False
    diloco_smoke_declared_artifact_supported: bool = False
    diloco_optimizer_smoke_declared_artifact_supported: bool = False
    integrated_diloco_smoke_declared_artifact_supported: bool = False
    parameter_fragment_smoke_declared_artifact_supported: bool = False
    bounded_diloco_experiment_declared_artifact_supported: bool = False
    tiny_real_training_smoke_declared_artifact_supported: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRemoteVSliceManifestArtifactPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("manifest artifact policy must remain offline")
        if self.policy_status == "manifest_artifact_policy_defined" and self.blockers:
            raise ValueError("defined manifest artifact policy cannot carry blockers")
        if (
            self.declared_artifact_path
            and self.declared_artifact_path not in self.declared_artifact_paths
        ):
            raise ValueError("primary declared artifact path must be manifest-declared")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _path_has_glob(text: str) -> bool:
    return any(token in text for token in ("*", "?", "[", "]", "{", "}"))


def _remote_path_is_safe_manifest_artifact(path: str) -> bool:
    parsed = PurePosixPath(path)
    text = str(parsed)
    return (
        parsed.is_absolute()
        and text.startswith("/tmp/")
        and parsed.suffix == ".json"
        and ".." not in parsed.parts
        and not _path_has_glob(text)
    )


def _declared_paths_from_manifest(manifest_path: str | Path) -> tuple[str, list[str], list[str]]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    blockers: list[str] = []
    paths: list[str] = []
    for entry in manifest.get("command_entries", []):
        raw_tokens = entry.get("argv_tokens")
        if isinstance(raw_tokens, list):
            tokens = [str(token) for token in raw_tokens]
        elif isinstance(entry.get("exact_command"), str):
            tokens = shlex.split(entry["exact_command"])
        else:
            tokens = []
        for index, token in enumerate(tokens):
            if token == "--out" and index + 1 < len(tokens):
                paths.append(tokens[index + 1])
    unique_paths = sorted(set(paths))
    if not unique_paths:
        blockers.append("manifest_declares_no_output_artifact_path")
    if len(unique_paths) > 1:
        blockers.append("manifest_declares_multiple_output_artifact_paths")
    for path in unique_paths:
        if not _remote_path_is_safe_manifest_artifact(path):
            blockers.append("declared_artifact_path_not_safe")
        if path not in SUPPORTED_MANIFEST_ARTIFACT_PATHS:
            blockers.append("declared_artifact_path_not_supported_by_safe_parser")
    return str(manifest.get("milestone", "unknown")), unique_paths, sorted(set(blockers))


def build_lambda_remote_vslice_manifest_artifact_policy_from_path(
    *,
    manifest: str | Path,
) -> LambdaRemoteVSliceManifestArtifactPolicy:
    milestone, paths, blockers = _declared_paths_from_manifest(manifest)
    path_set = set(paths)
    return LambdaRemoteVSliceManifestArtifactPolicy(
        milestone=milestone,
        policy_status="manifest_artifact_policy_defined" if not blockers else "blocked",
        declared_artifact_path=paths[0] if len(paths) == 1 else None,
        declared_artifact_paths=paths,
        runtime_smoke_declared_artifact_supported=(
            RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH in path_set
        ),
        synthetic_experiment_declared_artifact_supported=(
            SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH in path_set
        ),
        learner_syncer_declared_artifact_supported=(
            LEARNER_SYNCER_DECLARED_ARTIFACT_PATH in path_set
        ),
        diloco_smoke_declared_artifact_supported=(
            DILOCO_SMOKE_DECLARED_ARTIFACT_PATH in path_set
        ),
        diloco_optimizer_smoke_declared_artifact_supported=(
            DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH in path_set
        ),
        integrated_diloco_smoke_declared_artifact_supported=(
            INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH in path_set
        ),
        parameter_fragment_smoke_declared_artifact_supported=(
            PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH in path_set
        ),
        bounded_diloco_experiment_declared_artifact_supported=(
            BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH in path_set
        ),
        tiny_real_training_smoke_declared_artifact_supported=(
            TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH in path_set
        ),
        blockers=blockers,
        warnings=[
            "artifact capture is scoped to manifest-declared absolute /tmp JSON paths only",
        ],
    )


def _parser_for_declared_path(declared_remote_path: str, local_path: Path, max_bytes: int) -> Any:
    policy = {
        "declared_artifact_path": declared_remote_path,
        "max_content_bytes": max_bytes,
        "policy_status": "policy_defined",
    }
    if declared_remote_path == LEARNER_SYNCER_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.learner_syncer_artifact_parser import (
            parse_learner_syncer_artifact_file,
        )

        return parse_learner_syncer_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    if declared_remote_path == DILOCO_SMOKE_DECLARED_ARTIFACT_PATH:
        return parse_diloco_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    if declared_remote_path == DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH:
        return parse_diloco_optimizer_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    if declared_remote_path == INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH:
        return parse_integrated_diloco_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    if declared_remote_path == PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH:
        return parse_parameter_fragment_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    if declared_remote_path == BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH:
        return parse_bounded_diloco_experiment_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    if declared_remote_path == TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH:
        return parse_tiny_real_training_artifact_file(
            artifact_path=local_path,
            policy=policy,
        )
    return parse_runtime_smoke_artifact_file(
        artifact_path=local_path,
        policy=policy,
    )


def _capture_from_parser_report(
    *,
    declared_remote_path: str,
    local_path: Path,
    parser_report: Any,
) -> LambdaRemoteVSliceDeclaredArtifactCapture:
    if not parser_report.artifact_exists:
        return LambdaRemoteVSliceDeclaredArtifactCapture(
            declared_artifact_path=declared_remote_path,
            local_artifact_path=str(local_path),
            content_capture_status="artifact_absent",
            blockers=["artifact_absent"],
        )
    body_succeeded = parser_report.raw_content_persisted or parser_report.parsed_summary_persisted
    parse_status = parser_report.parse_status
    if (
        declared_remote_path == SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH
        and parse_status == "parsed_safe_runtime_smoke_artifact"
    ):
        parse_status = "parsed_safe_synthetic_experiment_artifact"
    elif (
        declared_remote_path == SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH
        and parse_status == "parsed_redacted_runtime_smoke_artifact"
    ):
        parse_status = "parsed_redacted_synthetic_experiment_artifact"
    return LambdaRemoteVSliceDeclaredArtifactCapture(
        declared_artifact_path=declared_remote_path,
        local_artifact_path=str(local_path),
        capture_succeeded=True,
        artifact_exists=True,
        artifact_bytes=parser_report.artifact_bytes,
        artifact_sha256=parser_report.artifact_sha256,
        artifact_secret_scan_passed=parser_report.secret_scan_passed,
        body_capture_attempted=True,
        body_capture_succeeded=body_succeeded,
        body_persisted=parser_report.raw_content_persisted,
        parsed_summary_persisted=parser_report.parsed_summary_persisted,
        safe_artifact_body=parser_report.safe_artifact_body,
        parsed_summary=parser_report.parsed_summary,
        parse_status=parse_status,
        content_capture_status=(
            "body_persisted"
            if parser_report.raw_content_persisted
            else "parsed_summary_persisted"
            if parser_report.parsed_summary_persisted
            else "metadata_only"
        ),
        warnings=parser_report.warnings,
        blockers=parser_report.blockers,
    )


def build_manifest_declared_artifact_capture_from_local_file(
    *,
    declared_remote_path: str,
    local_artifact_path: str | Path,
    manifest_declared_paths: list[str] | tuple[str, ...] | set[str],
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES,
) -> LambdaRemoteVSliceDeclaredArtifactCapture:
    manifest_path_set = set(manifest_declared_paths)
    if (
        declared_remote_path not in manifest_path_set
        or declared_remote_path not in SUPPORTED_MANIFEST_ARTIFACT_PATHS
        or not _remote_path_is_safe_manifest_artifact(declared_remote_path)
    ):
        return LambdaRemoteVSliceDeclaredArtifactCapture(
            declared_artifact_path=declared_remote_path,
            local_artifact_path=str(local_artifact_path),
            content_capture_status="blocked_undeclared_artifact_path",
            blockers=["undeclared_artifact_path"],
        )
    local_path = Path(local_artifact_path)
    if local_path.is_symlink():
        return LambdaRemoteVSliceDeclaredArtifactCapture(
            declared_artifact_path=declared_remote_path,
            local_artifact_path=str(local_path),
            artifact_exists=local_path.exists(),
            content_capture_status="blocked_artifact_symlink_escape",
            blockers=["artifact_symlink_escape_rejected"],
        )
    if local_path.exists() and not local_path.is_file():
        return LambdaRemoteVSliceDeclaredArtifactCapture(
            declared_artifact_path=declared_remote_path,
            local_artifact_path=str(local_path),
            artifact_exists=True,
            content_capture_status="blocked_artifact_path_not_file",
            blockers=["artifact_path_not_file"],
        )
    parser_report = _parser_for_declared_path(
        declared_remote_path,
        local_path,
        max_content_bytes,
    )
    return _capture_from_parser_report(
        declared_remote_path=declared_remote_path,
        local_path=local_path,
        parser_report=parser_report,
    )


def load_lambda_remote_vslice_manifest_artifact_policy(
    path: str | Path,
) -> LambdaRemoteVSliceManifestArtifactPolicy:
    return LambdaRemoteVSliceManifestArtifactPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_manifest_artifact_policy(
    path: str | Path,
    policy: LambdaRemoteVSliceManifestArtifactPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
