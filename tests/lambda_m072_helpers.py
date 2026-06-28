from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.first_experiment_success_record import (
    M068W_DEPENDENCY_BUNDLE_SHA256,
    M069R_SOURCE_BUNDLE_SHA256,
    M071R_OUTPUT_ARTIFACT_BYTES,
    M071R_OUTPUT_ARTIFACT_PATH,
    M071R_OUTPUT_ARTIFACT_SHA256,
    M071R_REQUIRED_STAGES,
)


def make_m071r_workdir(
    tmp_path: Path,
    *,
    training_attempted: bool = False,
    final_instance_count: int = 0,
) -> Path:
    workdir = tmp_path / "m071r"
    workdir.mkdir()
    stages = [
        {"stage": stage, "passed": True, "exit_code": 0}
        for stage in M071R_REQUIRED_STAGES
    ]
    report = {
        "run_id": "lambda-m071r-first-experiment",
        "selected_shape": "gpu_1x_a10",
        "selected_candidate": "gpu_1x_a10",
        "selected_region": "us-east-1",
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "source_bundle_hash_verified": True,
        "dependency_bundle_hash_verified": True,
        "local_dependency_install_succeeded": True,
        "vertical_slice_status": "vertical_slice_success",
        "failed_stage": None,
        "remote_command_stage_results": stages,
        "downloads_attempted": False,
        "training_attempted": training_attempted,
        "internet_install_attempted": False,
        "file_transfer_attempted": False,
        "port_forwarding_attempted": False,
        "termination_verified": True,
        "manual_review_required": False,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.1,
        "uploaded_bundles_count": 2,
        "experiment_output_artifact_capture_succeeded": True,
        "experiment_output_artifact_exists": True,
        "experiment_output_artifact_path": M071R_OUTPUT_ARTIFACT_PATH,
        "experiment_output_artifact_bytes": M071R_OUTPUT_ARTIFACT_BYTES,
        "experiment_output_artifact_sha256": M071R_OUTPUT_ARTIFACT_SHA256,
        "experiment_output_artifact_secret_scan_passed": True,
        "launch_ready": False,
        "launch_allowed": False,
    }
    evidence = {
        "stage_results": stages,
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "source_bundle_hash_verified": True,
        "dependency_bundle_hash_verified": True,
        "local_dependency_install_succeeded": True,
        "uploaded_bundles_count": 2,
        "vertical_slice_status": "vertical_slice_success",
        "downloads_attempted": False,
        "training_attempted": training_attempted,
        "internet_install_attempted": False,
        "file_transfer_attempted": False,
        "port_forwarding_attempted": False,
        "experiment_output_artifact_capture_succeeded": True,
        "experiment_output_artifact_exists": True,
        "experiment_output_artifact_path": M071R_OUTPUT_ARTIFACT_PATH,
        "experiment_output_artifact_bytes": M071R_OUTPUT_ARTIFACT_BYTES,
        "experiment_output_artifact_sha256": M071R_OUTPUT_ARTIFACT_SHA256,
        "experiment_output_artifact_secret_scan_passed": True,
    }
    (workdir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (workdir / "remote-vslice-evidence.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )
    (workdir / "spend-audit.json").write_text(
        json.dumps({"estimated_spend": 7.7}),
        encoding="utf-8",
    )
    (workdir / "post-discovery-summary-final.json").write_text(
        json.dumps(
            {
                "instance_count": final_instance_count,
                "unmanaged_count": 0,
                "launch_ready": False,
                "launch_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    return workdir


def write_bundle(path: Path, *, dependency: bool = False) -> Path:
    path.write_bytes(
        (
            M068W_DEPENDENCY_BUNDLE_SHA256
            if dependency
            else M069R_SOURCE_BUNDLE_SHA256
        ).encode("ascii")
    )
    return path
