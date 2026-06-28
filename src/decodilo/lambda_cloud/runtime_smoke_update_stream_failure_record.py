"""M075R3 runtime-smoke update-stream failure record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)

RuntimeSmokeUpdateStreamFailureStatus = Literal[
    "runtime_smoke_update_stream_failed",
    "not_runtime_smoke_update_stream_failed",
]


class LambdaRuntimeSmokeUpdateStreamFailureRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075U"
    failure_status: RuntimeSmokeUpdateStreamFailureStatus
    failed_stage: str | None = None
    failed_check: str | None = None
    error_classification: str | None = None
    safe_error: str | None = None
    expected_artifact_path: str = RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    artifact_body_persisted: bool
    parsed_summary_persisted: bool
    infrastructure_passed: bool
    source_upload_passed: bool
    dependency_upload_passed: bool
    dependency_install_passed: bool
    decodilo_import_passed: bool
    cli_help_passed: bool
    no_internet_install: bool
    no_downloads: bool
    no_training: bool
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_record(self) -> LambdaRuntimeSmokeUpdateStreamFailureRecord:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075U failure record must remain offline")
        if self.failure_status == "runtime_smoke_update_stream_failed" and self.blockers:
            raise ValueError("classified update-stream failure cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _post_summary_for_workdir(workdir: Path) -> dict[str, Any]:
    milestone = workdir.name.removeprefix("decodilo-lambda-")
    candidates = [
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary-final-4.json",
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary-final-3.json",
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary-final-2.json",
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary.json",
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-discovery.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return _read_json(candidate)
    return {}


def _stage(report: dict[str, Any], stage: str) -> dict[str, Any]:
    for item in report.get("remote_command_stage_results", []):
        if item.get("stage") == stage:
            return item
    return {}


def _stage_passed(report: dict[str, Any], stage: str) -> bool:
    return _stage(report, stage).get("passed") is True


def _artifact_body(report: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    body = report.get("experiment_output_artifact_body_json")
    if not isinstance(body, dict):
        body = evidence.get("experiment_output_artifact_body_json")
    return body if isinstance(body, dict) else {}


def _artifact_summary(report: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("experiment_output_artifact_parsed_summary")
    if not isinstance(summary, dict):
        summary = evidence.get("experiment_output_artifact_parsed_summary")
    return summary if isinstance(summary, dict) else {}


def build_lambda_runtime_smoke_update_stream_failure_record_from_paths(
    *,
    workdir: str | Path,
) -> LambdaRuntimeSmokeUpdateStreamFailureRecord:
    workdir_path = Path(workdir)
    report = _read_json(workdir_path / "report.json")
    evidence_path = workdir_path / "remote-vslice-evidence.json"
    evidence = _read_json(evidence_path) if evidence_path.is_file() else {}
    post = _post_summary_for_workdir(workdir_path)
    body = _artifact_body(report, evidence)
    summary = _artifact_summary(report, evidence)
    failed_check = str(summary.get("failed_check") or body.get("failed_check") or "")
    error_classification = str(
        summary.get("error_classification")
        or body.get("error_classification")
        or ""
    )
    safe_error = str(
        summary.get("safe_error_message") or body.get("safe_error_message") or ""
    )
    infrastructure_passed = all(
        [
            report.get("source_bundle_upload_succeeded") is True,
            report.get("dependency_bundle_upload_succeeded") is True,
            report.get("local_dependency_install_succeeded") is True,
            _stage_passed(report, "decodilo_import_check"),
            _stage_passed(report, "decodilo_cli_help_check"),
        ]
    )
    artifact_body_persisted = (
        report.get("experiment_output_artifact_body_persisted") is True
        or evidence.get("experiment_output_artifact_body_persisted") is True
    )
    parsed_summary_persisted = (
        report.get("experiment_output_artifact_parsed_summary_persisted") is True
        or evidence.get("experiment_output_artifact_parsed_summary_persisted") is True
    )
    blockers: list[str] = []
    if report.get("failed_stage") != "runtime_smoke_command":
        blockers.append("failed_stage_not_runtime_smoke_command")
    if report.get("vertical_slice_status") != "vertical_slice_failed_at_runtime_smoke_command":
        blockers.append("vertical_slice_status_not_runtime_smoke_failure")
    if failed_check != "protocol_or_event_check":
        blockers.append("failed_check_not_protocol_or_event_check")
    if error_classification != "update_stream_check_failed":
        blockers.append("error_classification_not_update_stream_check_failed")
    if safe_error != "update_stream_check_failed:TimeoutError":
        blockers.append("safe_error_not_update_stream_timeout")
    if not artifact_body_persisted:
        blockers.append("artifact_body_not_persisted")
    if not parsed_summary_persisted:
        blockers.append("parsed_summary_not_persisted")
    if not infrastructure_passed:
        blockers.append("infrastructure_not_passed")
    if report.get("experiment_output_artifact_path") != RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH:
        blockers.append("expected_artifact_path_mismatch")
    if report.get("experiment_output_artifact_secret_scan_passed") is not True:
        blockers.append("artifact_secret_scan_not_passed")
    if report.get("package_install_attempted") is not False:
        blockers.append("internet_install_or_package_install_attempted")
    if report.get("downloads_attempted") is not False:
        blockers.append("downloads_attempted")
    if report.get("training_attempted") is not False:
        blockers.append("training_attempted")
    if report.get("termination_verified") is not True:
        blockers.append("termination_not_verified")
    if post and (post.get("instance_count") != 0 or post.get("unmanaged_count") != 0):
        blockers.append("final_discovery_not_clean")
    status: RuntimeSmokeUpdateStreamFailureStatus = (
        "runtime_smoke_update_stream_failed"
        if not blockers
        else "not_runtime_smoke_update_stream_failed"
    )
    return LambdaRuntimeSmokeUpdateStreamFailureRecord(
        failure_status=status,
        failed_stage=report.get("failed_stage"),
        failed_check=failed_check or None,
        error_classification=error_classification or None,
        safe_error=safe_error or None,
        artifact_body_persisted=artifact_body_persisted,
        parsed_summary_persisted=parsed_summary_persisted,
        infrastructure_passed=infrastructure_passed,
        source_upload_passed=report.get("source_bundle_upload_succeeded") is True,
        dependency_upload_passed=report.get("dependency_bundle_upload_succeeded") is True,
        dependency_install_passed=report.get("local_dependency_install_succeeded") is True,
        decodilo_import_passed=_stage_passed(report, "decodilo_import_check"),
        cli_help_passed=_stage_passed(report, "decodilo_cli_help_check"),
        no_internet_install=report.get("package_install_attempted") is False,
        no_downloads=report.get("downloads_attempted") is False,
        no_training=report.get("training_attempted") is False,
        termination_verified=report.get("termination_verified") is True,
        final_instance_count=post.get("instance_count"),
        final_unmanaged_count=post.get("unmanaged_count"),
        historical_billable_action_performed=(
            report.get("billable_action_performed") is True
            or evidence.get("billable_action_performed") is True
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "M075U is offline; M075R3 billable activity is historical evidence only",
            "local runtime-smoke must pass before any future retry authorization",
        ],
    )


def load_lambda_runtime_smoke_update_stream_failure_record(
    path: str | Path,
) -> LambdaRuntimeSmokeUpdateStreamFailureRecord:
    return LambdaRuntimeSmokeUpdateStreamFailureRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_update_stream_failure_record(
    path: str | Path,
    record: LambdaRuntimeSmokeUpdateStreamFailureRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
