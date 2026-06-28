from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.first_experiment_command_discovery import (
    LambdaFirstExperimentCommandDiscovery,
    write_lambda_first_experiment_command_discovery,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    M068W_DEPENDENCY_BUNDLE_SHA256,
    M069R_REQUIRED_STAGES,
    M069R_SOURCE_BUNDLE_SHA256,
)


def make_m069r_workdir(tmp_path: Path, *, training_attempted: bool = False) -> Path:
    workdir = tmp_path / "m069r"
    workdir.mkdir()
    stages = [
        {"stage": stage, "passed": True, "exit_code": 0}
        for stage in M069R_REQUIRED_STAGES
    ]
    report = {
        "run_id": "test-m069r",
        "selected_shape": "gpu_1x_a10",
        "selected_region": "us-east-1",
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "source_bundle_hash_verified": True,
        "dependency_bundle_hash_verified": True,
        "local_dependency_install_succeeded": True,
        "vertical_slice_status": "vertical_slice_success",
        "failed_stage": None,
        "remote_command_stage_results": stages,
        "download_attempted": False,
        "downloads_attempted": False,
        "training_attempted": training_attempted,
        "internet_install_attempted": False,
        "port_forwarding_attempted": False,
        "termination_verified": True,
        "manual_review_required": False,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.1,
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
        "download_attempted": False,
        "training_attempted": training_attempted,
        "internet_install_attempted": False,
        "port_forwarding_attempted": False,
    }
    (workdir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (workdir / "remote-vslice-evidence.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )
    (workdir / "spend-audit.json").write_text(
        json.dumps({"conservative_estimated_spend": 1.5}),
        encoding="utf-8",
    )
    (workdir / "post-discovery-summary.json").write_text(
        json.dumps({"instance_count": 0, "unmanaged_count": 0}),
        encoding="utf-8",
    )
    return workdir


def make_discovery(path: Path) -> Path:
    report = LambdaFirstExperimentCommandDiscovery(
        discovery_status="safe_experiment_command_found",
        command_category="cli_profile_report_command",
        argv_tokens=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "ci-profile-report",
            "--out",
            "/tmp/decodilo-first-experiment-ci-profile-report.json",
        ],
        local_validation_command=["python", "-m", "decodilo.cli", "dev", "ci-profile-report"],
        local_validation_passed=True,
        timeout_seconds=30,
        safe_reason="test fixture",
    )
    write_lambda_first_experiment_command_discovery(path, report)
    return path


def make_bundle(path: Path, *, dependency: bool = False) -> Path:
    path.write_bytes(
        (
            M068W_DEPENDENCY_BUNDLE_SHA256
            if dependency
            else M069R_SOURCE_BUNDLE_SHA256
        ).encode("ascii")
    )
    return path
