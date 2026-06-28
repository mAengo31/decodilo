"""M075R2 runtime-smoke attempt closeout with artifact metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


class LambdaRuntimeSmokeAttemptCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075T"
    closeout_status: str
    closeout_succeeded: bool
    infrastructure_passed: bool
    source_upload_passed: bool
    dependency_upload_passed: bool
    dependency_install_passed: bool
    decodilo_import_passed: bool
    cli_help_passed: bool
    runtime_smoke_attempted: bool
    runtime_smoke_exit_code: int | None = None
    expected_artifact_path: str = RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    artifact_exists: bool
    artifact_size: int | None = None
    artifact_sha256: str | None = None
    artifact_secret_scan_passed: bool | None = None
    artifact_body_persisted: bool
    artifact_parsed_summary_persisted: bool
    failure_diagnosis_status: str
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
    def _validate_closeout(self) -> LambdaRuntimeSmokeAttemptCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075T closeout must remain offline")
        if self.closeout_succeeded and self.blockers:
            raise ValueError("successful M075T closeout cannot carry blockers")
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


def build_lambda_runtime_smoke_attempt_closeout_from_paths(
    *,
    workdir: str | Path,
) -> LambdaRuntimeSmokeAttemptCloseout:
    workdir_path = Path(workdir)
    report = _read_json(workdir_path / "report.json")
    evidence_path = workdir_path / "remote-vslice-evidence.json"
    evidence = _read_json(evidence_path) if evidence_path.is_file() else {}
    post = _post_summary_for_workdir(workdir_path)
    runtime_stage = _stage(report, "runtime_smoke_command")
    artifact_exists = report.get("experiment_output_artifact_exists") is True
    artifact_body_persisted = (
        report.get("experiment_output_artifact_body_persisted") is True
        or evidence.get("experiment_output_artifact_body_persisted") is True
    )
    artifact_summary_persisted = (
        report.get("experiment_output_artifact_parsed_summary_persisted") is True
        or evidence.get("experiment_output_artifact_parsed_summary_persisted") is True
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
    blockers: list[str] = []
    if report.get("failed_stage") != "runtime_smoke_command":
        blockers.append("failed_stage_not_runtime_smoke_command")
    if report.get("vertical_slice_status") != "vertical_slice_failed_at_runtime_smoke_command":
        blockers.append("vertical_slice_status_not_runtime_smoke_failure")
    if not infrastructure_passed:
        blockers.append("infrastructure_not_passed")
    if runtime_stage.get("exit_code") != 1:
        blockers.append("runtime_smoke_exit_code_not_one")
    if report.get("experiment_output_artifact_path") != RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH:
        blockers.append("expected_artifact_path_mismatch")
    if not artifact_exists:
        blockers.append("artifact_metadata_not_captured")
    if report.get("experiment_output_artifact_secret_scan_passed") is not True:
        blockers.append("artifact_secret_scan_not_passed")
    if report.get("termination_verified") is not True:
        blockers.append("termination_not_verified")
    if post and (post.get("instance_count") != 0 or post.get("unmanaged_count") != 0):
        blockers.append("final_discovery_not_clean")
    status = (
        "closed_runtime_smoke_command_failed_with_artifact_metadata_captured"
        if not blockers
        else "blocked"
    )
    diagnosis = (
        "artifact_body_or_summary_needed"
        if not artifact_body_persisted and not artifact_summary_persisted
        else "artifact_body_or_summary_available"
    )
    return LambdaRuntimeSmokeAttemptCloseout(
        closeout_status=status,
        closeout_succeeded=not blockers,
        infrastructure_passed=infrastructure_passed,
        source_upload_passed=report.get("source_bundle_upload_succeeded") is True,
        dependency_upload_passed=report.get("dependency_bundle_upload_succeeded") is True,
        dependency_install_passed=report.get("local_dependency_install_succeeded") is True,
        decodilo_import_passed=_stage_passed(report, "decodilo_import_check"),
        cli_help_passed=_stage_passed(report, "decodilo_cli_help_check"),
        runtime_smoke_attempted=bool(runtime_stage),
        runtime_smoke_exit_code=runtime_stage.get("exit_code"),
        artifact_exists=artifact_exists,
        artifact_size=report.get("experiment_output_artifact_bytes"),
        artifact_sha256=report.get("experiment_output_artifact_sha256"),
        artifact_secret_scan_passed=report.get(
            "experiment_output_artifact_secret_scan_passed"
        ),
        artifact_body_persisted=artifact_body_persisted,
        artifact_parsed_summary_persisted=artifact_summary_persisted,
        failure_diagnosis_status=diagnosis,
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
            "M075R2 infrastructure passed and artifact metadata was captured",
            "M075T requires future body or parsed-summary capture for diagnosis",
        ],
    )


def load_lambda_runtime_smoke_attempt_closeout(
    path: str | Path,
) -> LambdaRuntimeSmokeAttemptCloseout:
    return LambdaRuntimeSmokeAttemptCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_attempt_closeout(
    path: str | Path,
    closeout: LambdaRuntimeSmokeAttemptCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(closeout.to_json(), encoding="utf-8")
