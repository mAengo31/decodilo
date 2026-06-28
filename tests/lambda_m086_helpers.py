from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.integrated_diloco_success_record import (
    M068W_DEPENDENCY_BUNDLE_SHA256,
    M085R_INTEGRATED_ARTIFACT_BYTES,
    M085R_INTEGRATED_ARTIFACT_PATH,
    M085R_INTEGRATED_ARTIFACT_SHA256,
    M085R_REQUIRED_STAGES,
    M085R_SOURCE_BUNDLE_SHA256,
)


def make_m085r_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "m085r"
    workdir.mkdir()
    stage_results = [
        {
            "stage": stage,
            "passed": True,
            "exit_code": 0,
            "stdout_truncated": False,
            "stderr_truncated": False,
        }
        for stage in M085R_REQUIRED_STAGES
    ]
    artifact_body = {
        "integrated_diloco_smoke_status": "passed",
        "optimization_fidelity": "integrated_optimizer_protocol_smoke",
        "inner_optimizer_semantics": "adamw",
        "outer_optimizer_semantics": "nesterov",
        "parameter_fragment_semantics": "not_exercised",
        "protocol_optimizer_link_check_passed": True,
        "pseudo_gradient_check_passed": True,
        "inner_adamw_check_passed": True,
        "outer_nesterov_check_passed": True,
        "optimizer_state_roundtrip_check_passed": True,
        "replay_or_metric_check_passed": True,
        "reference_value_check_passed": True,
        "max_abs_error": 0.0,
        "network_used": False,
        "package_install_attempted": False,
        "download_attempted": False,
        "training_attempted": False,
        "real_model_training_attempted": False,
        "torch_required": False,
        "gpu_required": False,
        "background_process_started": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    base = {
        "run_id": "lambda-m085r-integrated-diloco-smoke",
        "selected_candidate": "gpu_1x_a10",
        "selected_shape": "gpu_1x_a10",
        "selected_region": "us-west-1",
        "source_bundle_sha256": M085R_SOURCE_BUNDLE_SHA256,
        "dependency_bundle_sha256": M068W_DEPENDENCY_BUNDLE_SHA256,
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "source_bundle_hash_verified": True,
        "dependency_bundle_hash_verified": True,
        "local_dependency_install_succeeded": True,
        "readonly_verify_running_result": "running",
        "host_discovery_status": "FOUND",
        "ssh_port_reachable": True,
        "ssh_attempted": True,
        "remote_command_result": "succeeded",
        "vertical_slice_status": "vertical_slice_success",
        "failed_stage": None,
        "launch_request_sent": True,
        "experiment_output_artifact_exists": True,
        "experiment_output_artifact_capture_succeeded": True,
        "experiment_output_artifact_path": M085R_INTEGRATED_ARTIFACT_PATH,
        "experiment_output_artifact_bytes": M085R_INTEGRATED_ARTIFACT_BYTES,
        "experiment_output_artifact_sha256": M085R_INTEGRATED_ARTIFACT_SHA256,
        "experiment_output_artifact_secret_scan_passed": True,
        "experiment_output_artifact_body_persisted": True,
        "experiment_output_artifact_parsed_summary_persisted": True,
        "experiment_output_artifact_body_json": artifact_body,
        "experiment_output_artifact_parsed_summary": artifact_body,
        "downloads_attempted": False,
        "training_attempted": False,
        "internet_install_attempted": False,
        "package_install_attempted": False,
        "unapproved_file_transfer_attempted": False,
        "extra_file_transfer_attempted": False,
        "arbitrary_file_read_attempted": False,
        "port_forwarding_attempted": False,
        "termination_verified": True,
        "manual_review_required": False,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.1014292691,
        "launch_ready": False,
        "launch_allowed": False,
    }
    evidence = {
        **base,
        "stage_results": stage_results,
        "uploaded_bundles_count": 2,
        "ssh_banner_ready": True,
        "ssh_banner_prefix_observed": True,
        "billable_action_performed": False,
    }
    _write_json(workdir / "report.json", {**base, "remote_command_stage_results": stage_results})
    _write_json(workdir / "remote-vslice-evidence.json", evidence)
    _write_json(
        workdir / "spend-audit.json",
        {
            "billable_action_performed": True,
            "estimated_spend": 7.8627340393,
            "budget_exceeded": False,
            "launch_request_sent": True,
            "terminate_request_sent": True,
            "termination_verified": True,
        },
    )
    _write_json(
        workdir / "post-discovery-summary.json",
        {
            "instance_count": 0,
            "unmanaged_count": 0,
            "manual_review_required": False,
            "mutating_operations": 0,
            "billable_action_performed": False,
            "launch_ready": False,
            "launch_allowed": False,
        },
    )
    return workdir


def write_m086_integrated_closeout_chain(
    tmp_path: Path,
    workdir: Path,
) -> dict[str, Path]:
    from decodilo.lambda_cloud.integrated_diloco_closeout import (
        build_lambda_integrated_diloco_closeout_from_paths,
        write_lambda_integrated_diloco_closeout,
    )
    from decodilo.lambda_cloud.integrated_diloco_evidence_package import (
        build_lambda_integrated_diloco_evidence_package_from_paths,
        write_lambda_integrated_diloco_evidence_package,
    )
    from decodilo.lambda_cloud.integrated_diloco_reconciliation import (
        build_lambda_integrated_diloco_reconciliation_from_paths,
        write_lambda_integrated_diloco_reconciliation,
    )
    from decodilo.lambda_cloud.integrated_diloco_success_record import (
        build_lambda_integrated_diloco_success_record_from_paths,
        write_lambda_integrated_diloco_success_record,
    )

    success_path = tmp_path / "integrated-success.json"
    reconciliation_path = tmp_path / "integrated-reconciliation.json"
    evidence_path = tmp_path / "integrated-evidence.json"
    closeout_path = tmp_path / "integrated-closeout.json"
    write_lambda_integrated_diloco_success_record(
        success_path,
        build_lambda_integrated_diloco_success_record_from_paths(workdir=workdir),
    )
    write_lambda_integrated_diloco_reconciliation(
        reconciliation_path,
        build_lambda_integrated_diloco_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )
    write_lambda_integrated_diloco_evidence_package(
        evidence_path,
        build_lambda_integrated_diloco_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )
    write_lambda_integrated_diloco_closeout(
        closeout_path,
        build_lambda_integrated_diloco_closeout_from_paths(
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


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
