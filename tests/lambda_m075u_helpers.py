from __future__ import annotations

import json
from pathlib import Path

from decodilo.dev.runtime_smoke import run_runtime_smoke
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)

M075R3_UPDATE_STREAM_SHA = (
    "14b3f9001f25541c38213c4c64d0ab0b18f2a1da2984bc40814dd21eeee7c647"
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_m075r3_update_stream_failure_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "decodilo-lambda-m075r3-test"
    workdir.mkdir()
    artifact_body = {
        "runtime_smoke_status": "failed",
        "failed_check": "protocol_or_event_check",
        "error_classification": "update_stream_check_failed",
        "safe_error_message": "update_stream_check_failed:TimeoutError",
        "protocol_or_event_check_passed": False,
        "replay_or_metric_check_passed": True,
        "network_used": False,
        "package_install_attempted": False,
        "download_attempted": False,
        "training_attempted": False,
        "torch_required": False,
        "gpu_required": False,
        "background_process_started": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    artifact_summary = {
        "runtime_smoke_status": "failed",
        "failed_check": "protocol_or_event_check",
        "error_classification": "update_stream_check_failed",
        "safe_error_message": "update_stream_check_failed:TimeoutError",
        "network_used": False,
        "package_install_attempted": False,
        "download_attempted": False,
        "training_attempted": False,
        "torch_required": False,
        "gpu_required": False,
        "background_process_started": False,
    }
    stage_results = [
        {"stage": "decodilo_import_check", "passed": True, "exit_code": 0},
        {"stage": "decodilo_cli_help_check", "passed": True, "exit_code": 0},
        {
            "stage": "runtime_smoke_command",
            "passed": False,
            "exit_code": 1,
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
        "experiment_output_artifact_path": RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
        "experiment_output_artifact_exists": True,
        "experiment_output_artifact_bytes": 1367,
        "experiment_output_artifact_sha256": M075R3_UPDATE_STREAM_SHA,
        "experiment_output_artifact_secret_scan_passed": True,
        "experiment_output_artifact_body_persisted": True,
        "experiment_output_artifact_parsed_summary_persisted": True,
        "experiment_output_artifact_body_json": artifact_body,
        "experiment_output_artifact_parsed_summary": artifact_summary,
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
    summary_path = Path("/tmp/decodilo-lambda-post-m075r3-test-summary-final-3.json")
    write_json(summary_path, post)
    return workdir


def make_runtime_smoke_report(path: Path):
    return run_runtime_smoke(synthetic=True, max_steps=1, out=path)
