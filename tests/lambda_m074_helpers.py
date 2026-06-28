from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.tiny_smoke_success_record import (
    M068W_DEPENDENCY_BUNDLE_SHA256,
    M073R2_REQUIRED_STAGES,
    M073R2_SOURCE_BUNDLE_SHA256,
    M073R2_TINY_SMOKE_ARTIFACT_BYTES,
    M073R2_TINY_SMOKE_ARTIFACT_PATH,
    M073R2_TINY_SMOKE_ARTIFACT_SHA256,
)


def make_m073r2_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "m073r2"
    workdir.mkdir()
    stage_results = [
        {
            "stage": stage,
            "passed": True,
            "exit_code": 0,
            "stdout_truncated": False,
            "stderr_truncated": False,
        }
        for stage in M073R2_REQUIRED_STAGES
    ]
    base = {
        "run_id": "lambda-m073r-tiny-smoke",
        "selected_candidate": "gpu_1x_a10",
        "selected_shape": "gpu_1x_a10",
        "selected_region": "us-east-1",
        "source_bundle_sha256": M073R2_SOURCE_BUNDLE_SHA256,
        "dependency_bundle_sha256": M068W_DEPENDENCY_BUNDLE_SHA256,
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "source_bundle_hash_verified": True,
        "dependency_bundle_hash_verified": True,
        "local_dependency_install_succeeded": True,
        "vertical_slice_status": "vertical_slice_success",
        "failed_stage": None,
        "experiment_output_artifact_exists": True,
        "experiment_output_artifact_capture_succeeded": True,
        "experiment_output_artifact_path": M073R2_TINY_SMOKE_ARTIFACT_PATH,
        "experiment_output_artifact_bytes": M073R2_TINY_SMOKE_ARTIFACT_BYTES,
        "experiment_output_artifact_sha256": M073R2_TINY_SMOKE_ARTIFACT_SHA256,
        "experiment_output_artifact_secret_scan_passed": True,
        "downloads_attempted": False,
        "training_attempted": False,
        "internet_install_attempted": False,
        "package_install_attempted": False,
        "file_transfer_attempted": False,
        "unapproved_file_transfer_attempted": False,
        "port_forwarding_attempted": False,
        "termination_verified": True,
        "manual_review_required": False,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.11152415958373653,
        "launch_ready": False,
        "launch_allowed": False,
    }
    report = {**base, "remote_command_stage_results": stage_results}
    evidence = {
        **base,
        "stage_results": stage_results,
        "uploaded_bundles_count": 2,
        "ssh_banner_ready": True,
        "ssh_banner_prefix_observed": True,
        "billable_action_performed": False,
    }
    spend = {
        "billable_action_performed": True,
        "estimated_spend": 8.645283688661747,
        "budget_exceeded": False,
        "launch_request_sent": True,
        "terminate_request_sent": True,
        "termination_verified": True,
    }
    post_summary = {
        "instance_count": 0,
        "unmanaged_count": 0,
        "manual_review_required": False,
        "mutating_operations": 0,
        "billable_action_performed": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    _write_json(workdir / "report.json", report)
    _write_json(workdir / "remote-vslice-evidence.json", evidence)
    _write_json(workdir / "spend-audit.json", spend)
    _write_json(workdir / "post-discovery-summary.json", post_summary)
    return workdir


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_m074_closeout_chain(tmp_path: Path, workdir: Path) -> dict[str, Path]:
    from decodilo.lambda_cloud.tiny_smoke_closeout import (
        build_lambda_tiny_smoke_closeout_from_paths,
        write_lambda_tiny_smoke_closeout,
    )
    from decodilo.lambda_cloud.tiny_smoke_evidence_package import (
        build_lambda_tiny_smoke_evidence_package_from_paths,
        write_lambda_tiny_smoke_evidence_package,
    )
    from decodilo.lambda_cloud.tiny_smoke_reconciliation import (
        build_lambda_tiny_smoke_reconciliation_from_paths,
        write_lambda_tiny_smoke_reconciliation,
    )
    from decodilo.lambda_cloud.tiny_smoke_success_record import (
        build_lambda_tiny_smoke_success_record_from_paths,
        write_lambda_tiny_smoke_success_record,
    )

    success_path = tmp_path / "success.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    evidence_path = tmp_path / "evidence.json"
    closeout_path = tmp_path / "closeout.json"
    write_lambda_tiny_smoke_success_record(
        success_path,
        build_lambda_tiny_smoke_success_record_from_paths(workdir=workdir),
    )
    write_lambda_tiny_smoke_reconciliation(
        reconciliation_path,
        build_lambda_tiny_smoke_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )
    write_lambda_tiny_smoke_evidence_package(
        evidence_path,
        build_lambda_tiny_smoke_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )
    write_lambda_tiny_smoke_closeout(
        closeout_path,
        build_lambda_tiny_smoke_closeout_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
            evidence_package=evidence_path,
        ),
    )
    return {
        "success": success_path,
        "reconciliation": reconciliation_path,
        "evidence": evidence_path,
        "closeout": closeout_path,
    }
