"""Offline M075R runtime-smoke failure classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vertical_slice_policy import M075R_OUTPUT_ARTIFACT_PATH

RuntimeSmokeFailureStatus = Literal[
    "runtime_smoke_command_failed",
    "not_runtime_smoke_command_failed",
]


class LambdaRuntimeSmokeFailureRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    failure_status: RuntimeSmokeFailureStatus
    infrastructure_passed: bool
    source_upload_passed: bool
    dependency_upload_passed: bool
    dependency_install_passed: bool
    decodilo_import_passed: bool
    cli_help_passed: bool
    runtime_smoke_attempted: bool
    runtime_smoke_exit_code: int | None = None
    stderr_empty: bool
    stdout_redacted_hash_present: bool
    expected_artifact_path: str = M075R_OUTPUT_ARTIFACT_PATH
    expected_artifact_metadata_captured: bool
    expected_artifact_contents_captured: bool = False
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
    def _validate_record(self) -> LambdaRuntimeSmokeFailureRecord:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075S failure record must not authorize launch or spend")
        if self.failure_status == "runtime_smoke_command_failed" and self.blockers:
            raise ValueError("classified M075R failure record cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _post_summary_for_workdir(workdir: Path) -> dict[str, Any]:
    milestone = workdir.name.removeprefix("decodilo-lambda-")
    candidates = [
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary-final-3.json",
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary-final-2.json",
        Path("/tmp") / f"decodilo-lambda-post-{milestone}-summary.json",
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


def build_lambda_runtime_smoke_failure_record_from_paths(
    *,
    workdir: str | Path,
) -> LambdaRuntimeSmokeFailureRecord:
    workdir_path = Path(workdir)
    report = _read_json(workdir_path / "report.json")
    evidence_path = workdir_path / "remote-vslice-evidence.json"
    evidence = _read_json(evidence_path) if evidence_path.is_file() else {}
    post = _post_summary_for_workdir(workdir_path)
    runtime_stage = _stage(report, "runtime_smoke_command")
    blockers: list[str] = []
    if report.get("failed_stage") != "runtime_smoke_command":
        blockers.append("failed_stage_not_runtime_smoke_command")
    if report.get("vertical_slice_status") != "vertical_slice_failed_at_runtime_smoke_command":
        blockers.append("vertical_slice_status_not_runtime_smoke_failure")
    infrastructure_passed = all(
        [
            report.get("source_bundle_upload_succeeded") is True,
            report.get("dependency_bundle_upload_succeeded") is True,
            report.get("local_dependency_install_succeeded") is True,
            _stage_passed(report, "decodilo_import_check"),
            _stage_passed(report, "decodilo_cli_help_check"),
        ]
    )
    if not infrastructure_passed:
        blockers.append("infrastructure_not_passed")
    if report.get("termination_verified") is not True:
        blockers.append("termination_not_verified")
    if post and (post.get("instance_count") != 0 or post.get("unmanaged_count") != 0):
        blockers.append("final_discovery_not_clean")

    stderr_hash = runtime_stage.get("stderr_sha256_prefix")
    stderr_empty = (
        runtime_stage.get("stderr_redacted_present") is False
        and stderr_hash == "e3b0c44298fc1c14"
    )
    stdout_hash_present = bool(runtime_stage.get("stdout_sha256_prefix"))
    artifact_metadata_captured = (
        report.get("experiment_output_artifact_capture_succeeded") is True
        and report.get("experiment_output_artifact_path") == M075R_OUTPUT_ARTIFACT_PATH
    )
    status: RuntimeSmokeFailureStatus = (
        "runtime_smoke_command_failed" if not blockers else "not_runtime_smoke_command_failed"
    )
    return LambdaRuntimeSmokeFailureRecord(
        failure_status=status,
        infrastructure_passed=infrastructure_passed,
        source_upload_passed=report.get("source_bundle_upload_succeeded") is True,
        dependency_upload_passed=report.get("dependency_bundle_upload_succeeded") is True,
        dependency_install_passed=report.get("local_dependency_install_succeeded") is True,
        decodilo_import_passed=_stage_passed(report, "decodilo_import_check"),
        cli_help_passed=_stage_passed(report, "decodilo_cli_help_check"),
        runtime_smoke_attempted=bool(runtime_stage),
        runtime_smoke_exit_code=runtime_stage.get("exit_code"),
        stderr_empty=stderr_empty,
        stdout_redacted_hash_present=stdout_hash_present,
        expected_artifact_metadata_captured=artifact_metadata_captured,
        failure_diagnosis_status=(
            "insufficient_failure_artifact_evidence"
            if not artifact_metadata_captured
            else "failure_artifact_metadata_available"
        ),
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
        blockers=blockers,
        warnings=[
            "M075R infrastructure passed",
            "diagnosis is limited by missing failure artifact metadata",
        ],
    )


def load_lambda_runtime_smoke_failure_record(
    path: str | Path,
) -> LambdaRuntimeSmokeFailureRecord:
    return LambdaRuntimeSmokeFailureRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_failure_record(
    path: str | Path,
    record: LambdaRuntimeSmokeFailureRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
