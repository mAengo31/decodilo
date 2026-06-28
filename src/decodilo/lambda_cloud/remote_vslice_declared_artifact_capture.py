"""Declared-artifact capture helpers for remote vertical-slice evidence."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    DEFAULT_MAX_CONTENT_BYTES,
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
    parse_runtime_smoke_artifact_file,
)

SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-synthetic-experiment.json"
)
LEARNER_SYNCER_SMOKE_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-learner-syncer-smoke.json"
)
DILOCO_SMOKE_DECLARED_ARTIFACT_PATH = "/tmp/decodilo-diloco-smoke.json"
DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-diloco-optimizer-smoke.json"
)
INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-integrated-diloco-smoke.json"
)
PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-parameter-fragment-smoke.json"
)
BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-bounded-diloco-experiment.json"
)
TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH = (
    "/tmp/decodilo-tiny-real-training-smoke.json"
)
DECLARED_ARTIFACT_PATHS = {
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
    SYNTHETIC_EXPERIMENT_DECLARED_ARTIFACT_PATH,
    LEARNER_SYNCER_SMOKE_DECLARED_ARTIFACT_PATH,
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH,
    INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
    PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH,
    BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH,
    TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH,
}


class LambdaRemoteVSliceDeclaredArtifactCapture(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075T"
    declared_artifact_path: str = RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    local_artifact_path: str | None = None
    capture_attempted: bool = True
    capture_succeeded: bool = False
    artifact_exists: bool = False
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    artifact_secret_scan_passed: bool | None = None
    body_capture_attempted: bool = False
    body_capture_succeeded: bool = False
    body_persisted: bool = False
    parsed_summary_persisted: bool = False
    safe_artifact_body: dict[str, Any] | None = None
    parsed_summary: dict[str, Any] | None = None
    parse_status: str | None = None
    content_capture_status: str
    no_arbitrary_file_read: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_capture(self) -> LambdaRemoteVSliceDeclaredArtifactCapture:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("declared artifact capture must not authorize launch")
        if self.body_persisted and not self.body_capture_succeeded:
            raise ValueError("body cannot be persisted unless capture succeeded")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"

    def evidence_fields(self) -> dict[str, Any]:
        return {
            "experiment_output_artifact_capture_succeeded": self.capture_succeeded,
            "experiment_output_artifact_exists": self.artifact_exists,
            "experiment_output_artifact_bytes": self.artifact_bytes,
            "experiment_output_artifact_sha256": self.artifact_sha256,
            "experiment_output_artifact_secret_scan_passed": self.artifact_secret_scan_passed,
            "experiment_output_artifact_body_capture_attempted": self.body_capture_attempted,
            "experiment_output_artifact_body_capture_succeeded": self.body_capture_succeeded,
            "experiment_output_artifact_body_persisted": self.body_persisted,
            "experiment_output_artifact_body_json": self.safe_artifact_body,
            "experiment_output_artifact_parsed_summary_persisted": self.parsed_summary_persisted,
            "experiment_output_artifact_parsed_summary": self.parsed_summary,
            "experiment_output_artifact_parse_status": self.parse_status,
            "experiment_output_artifact_content_capture_status": self.content_capture_status,
        }


def _remote_path_is_allowed(remote_path: str, declared_path: str) -> bool:
    parsed = PurePosixPath(remote_path)
    return (
        remote_path == declared_path
        and parsed.is_absolute()
        and ".." not in parsed.parts
        and parsed.suffix == ".json"
    )


def build_declared_artifact_capture_from_local_file(
    *,
    declared_remote_path: str,
    local_artifact_path: str | Path,
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES,
) -> LambdaRemoteVSliceDeclaredArtifactCapture:
    if declared_remote_path not in DECLARED_ARTIFACT_PATHS or not _remote_path_is_allowed(
        declared_remote_path,
        declared_remote_path,
    ):
        return LambdaRemoteVSliceDeclaredArtifactCapture(
            declared_artifact_path=declared_remote_path,
            local_artifact_path=str(local_artifact_path),
            content_capture_status="blocked_undeclared_artifact_path",
            blockers=["undeclared_artifact_path"],
        )
    local_path = Path(local_artifact_path)
    if local_path.exists() and not local_path.is_file():
        return LambdaRemoteVSliceDeclaredArtifactCapture(
            declared_artifact_path=declared_remote_path,
            local_artifact_path=str(local_path),
            artifact_exists=True,
            content_capture_status="blocked_artifact_path_not_file",
            blockers=["artifact_path_not_file"],
        )
    if declared_remote_path == LEARNER_SYNCER_SMOKE_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.learner_syncer_artifact_parser import (
            parse_learner_syncer_artifact_file,
        )

        parser_report = parse_learner_syncer_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    elif declared_remote_path == DILOCO_SMOKE_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.diloco_artifact_parser import (
            parse_diloco_artifact_file,
        )

        parser_report = parse_diloco_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    elif declared_remote_path == DILOCO_OPTIMIZER_SMOKE_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.diloco_optimizer_artifact_parser import (
            parse_diloco_optimizer_artifact_file,
        )

        parser_report = parse_diloco_optimizer_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    elif declared_remote_path == INTEGRATED_DILOCO_SMOKE_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.integrated_diloco_artifact_parser import (
            parse_integrated_diloco_artifact_file,
        )

        parser_report = parse_integrated_diloco_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    elif declared_remote_path == PARAMETER_FRAGMENT_SMOKE_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.parameter_fragment_artifact_parser import (
            parse_parameter_fragment_artifact_file,
        )

        parser_report = parse_parameter_fragment_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    elif declared_remote_path == BOUNDED_DILOCO_EXPERIMENT_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_parser import (
            parse_bounded_diloco_experiment_artifact_file,
        )

        parser_report = parse_bounded_diloco_experiment_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    elif declared_remote_path == TINY_REAL_TRAINING_SMOKE_DECLARED_ARTIFACT_PATH:
        from decodilo.lambda_cloud.tiny_real_training_artifact_parser import (
            parse_tiny_real_training_artifact_file,
        )

        parser_report = parse_tiny_real_training_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
    else:
        parser_report = parse_runtime_smoke_artifact_file(
            artifact_path=local_path,
            policy={
                "declared_artifact_path": declared_remote_path,
                "max_content_bytes": max_content_bytes,
            },
        )
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


def load_lambda_remote_vslice_declared_artifact_capture(
    path: str | Path,
) -> LambdaRemoteVSliceDeclaredArtifactCapture:
    return LambdaRemoteVSliceDeclaredArtifactCapture.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_declared_artifact_capture(
    path: str | Path,
    capture: LambdaRemoteVSliceDeclaredArtifactCapture,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(capture.to_json(), encoding="utf-8")
