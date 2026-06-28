from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    LambdaM075RRuntimeProtocolSmokeAuthorization,
    write_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    M075R_OUTPUT_ARTIFACT_PATH,
    M075R_RUNTIME_SMOKE_COMMAND,
    LambdaRemoteVerticalSliceCommandEntry,
    LambdaRemoteVerticalSliceCommandManifest,
    render_lambda_remote_vertical_slice_argv,
    write_lambda_remote_vertical_slice_command_manifest,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_m075r_runtime_smoke_failure_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "decodilo-lambda-m075r-test"
    workdir.mkdir()
    stage_results = [
        {"stage": "decodilo_import_check", "passed": True, "exit_code": 0},
        {"stage": "decodilo_cli_help_check", "passed": True, "exit_code": 0},
        {
            "stage": "runtime_smoke_command",
            "passed": False,
            "exit_code": 1,
            "stderr_redacted_present": False,
            "stderr_sha256_prefix": "e3b0c44298fc1c14",
            "stdout_sha256_prefix": "28cf0624064abd17",
        },
    ]
    report = {
        "failed_stage": "runtime_smoke_command",
        "vertical_slice_status": "vertical_slice_failed_at_runtime_smoke_command",
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "local_dependency_install_succeeded": True,
        "remote_command_stage_results": stage_results,
        "package_install_attempted": False,
        "downloads_attempted": False,
        "training_attempted": False,
        "termination_verified": True,
        "billable_action_performed": True,
        "experiment_output_artifact_capture_succeeded": False,
        "experiment_output_artifact_path": None,
        "launch_ready": False,
        "launch_allowed": False,
    }
    evidence = {
        "failed_stage": "runtime_smoke_command",
        "vertical_slice_status": "vertical_slice_failed_at_runtime_smoke_command",
        "billable_action_performed": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    post = {
        "instance_count": 0,
        "unmanaged_count": 0,
        "launch_ready": False,
        "launch_allowed": False,
    }
    write_json(workdir / "report.json", report)
    write_json(workdir / "remote-vslice-evidence.json", evidence)
    summary_path = Path("/tmp/decodilo-lambda-post-m075r-test-summary-final-3.json")
    write_json(summary_path, post)
    return workdir


def make_m075r2_runtime_smoke_metadata_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "decodilo-lambda-m075r2-test"
    workdir.mkdir()
    stage_results = [
        {"stage": "decodilo_import_check", "passed": True, "exit_code": 0},
        {"stage": "decodilo_cli_help_check", "passed": True, "exit_code": 0},
        {
            "stage": "runtime_smoke_command",
            "passed": False,
            "exit_code": 1,
            "stderr_redacted_present": False,
            "stderr_sha256_prefix": "e3b0c44298fc1c14",
            "stdout_sha256_prefix": "28cf0624064abd17",
        },
    ]
    report = {
        "failed_stage": "runtime_smoke_command",
        "vertical_slice_status": "vertical_slice_failed_at_runtime_smoke_command",
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "local_dependency_install_succeeded": True,
        "remote_command_stage_results": stage_results,
        "package_install_attempted": False,
        "downloads_attempted": False,
        "training_attempted": False,
        "termination_verified": True,
        "billable_action_performed": True,
        "experiment_output_artifact_capture_succeeded": True,
        "experiment_output_artifact_path": M075R_OUTPUT_ARTIFACT_PATH,
        "experiment_output_artifact_exists": True,
        "experiment_output_artifact_bytes": 1367,
        "experiment_output_artifact_sha256": (
            "8be26ec2469bddca7d72b714917fa0071bea97663ef6fced7374c4f6dc7af439"
        ),
        "experiment_output_artifact_secret_scan_passed": True,
        "experiment_output_artifact_body_persisted": False,
        "experiment_output_artifact_parsed_summary_persisted": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    evidence = {
        "failed_stage": "runtime_smoke_command",
        "vertical_slice_status": "vertical_slice_failed_at_runtime_smoke_command",
        "billable_action_performed": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    post = {
        "instance_count": 0,
        "unmanaged_count": 0,
        "manual_review_required": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    write_json(workdir / "report.json", report)
    write_json(workdir / "remote-vslice-evidence.json", evidence)
    summary_path = Path("/tmp/decodilo-lambda-post-m075r2-test-summary-final-3.json")
    write_json(summary_path, post)
    return workdir


def make_m075r_manifest(path: Path) -> Path:
    entry = LambdaRemoteVerticalSliceCommandEntry(
        stage="runtime_smoke_command",
        exact_command=render_lambda_remote_vertical_slice_argv(
            M075R_RUNTIME_SMOKE_COMMAND
        ),
        argv_tokens=list(M075R_RUNTIME_SMOKE_COMMAND),
        timeout_seconds=30,
        failure_stage_if_nonzero="runtime_smoke_command",
    )
    write_lambda_remote_vertical_slice_command_manifest(
        path,
        LambdaRemoteVerticalSliceCommandManifest(
            milestone="M075R",
            max_remote_commands=1,
            command_entries=[entry],
        ),
    )
    return path


def make_runtime_authorization(path: Path) -> Path:
    write_lambda_m075r_runtime_protocol_smoke_authorization(
        path,
        LambdaM075RRuntimeProtocolSmokeAuthorization(
            authorization_status="authorized_for_future_m075r_runtime_protocol_smoke",
            command_category="dev_runtime_smoke_synthetic",
        ),
    )
    return path


def expected_artifact_path() -> str:
    return M075R_OUTPUT_ARTIFACT_PATH
