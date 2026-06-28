from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.diloco_optimizer_success_record import (
    M068W_DEPENDENCY_BUNDLE_SHA256,
    M083R_OPTIMIZER_ARTIFACT_BYTES,
    M083R_OPTIMIZER_ARTIFACT_PATH,
    M083R_OPTIMIZER_ARTIFACT_SHA256,
    M083R_REQUIRED_STAGES,
    M083R_SOURCE_BUNDLE_SHA256,
)
from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
    LambdaLearnerSyncerSmokeCloseout,
    write_lambda_learner_syncer_smoke_closeout,
)


def make_m083r_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "m083r"
    workdir.mkdir()
    stage_results = [
        {
            "stage": stage,
            "passed": True,
            "exit_code": 0,
            "stdout_truncated": False,
            "stderr_truncated": False,
        }
        for stage in M083R_REQUIRED_STAGES
    ]
    artifact_body = {
        "diloco_optimizer_smoke_status": "passed",
        "optimization_fidelity": "optimizer_semantics_smoke",
        "inner_optimizer_semantics": "adamw",
        "outer_optimizer_semantics": "nesterov",
        "parameter_fragment_semantics": "not_exercised",
        "pseudo_gradient_check_passed": True,
        "inner_adamw_check_passed": True,
        "outer_nesterov_check_passed": True,
        "optimizer_state_roundtrip_check_passed": True,
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
        "run_id": "lambda-m083r-diloco-optimizer-smoke",
        "selected_candidate": "gpu_1x_a10",
        "selected_shape": "gpu_1x_a10",
        "selected_region": "us-west-1",
        "source_bundle_sha256": M083R_SOURCE_BUNDLE_SHA256,
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
        "experiment_output_artifact_path": M083R_OPTIMIZER_ARTIFACT_PATH,
        "experiment_output_artifact_bytes": M083R_OPTIMIZER_ARTIFACT_BYTES,
        "experiment_output_artifact_sha256": M083R_OPTIMIZER_ARTIFACT_SHA256,
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
        "estimated_spend": 0.097742479,
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
            "estimated_spend": 7.5769363576,
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


def write_m084_optimizer_closeout_chain(tmp_path: Path, workdir: Path) -> dict[str, Path]:
    from decodilo.lambda_cloud.diloco_optimizer_closeout import (
        build_lambda_diloco_optimizer_closeout_from_paths,
        write_lambda_diloco_optimizer_closeout,
    )
    from decodilo.lambda_cloud.diloco_optimizer_evidence_package import (
        build_lambda_diloco_optimizer_evidence_package_from_paths,
        write_lambda_diloco_optimizer_evidence_package,
    )
    from decodilo.lambda_cloud.diloco_optimizer_reconciliation import (
        build_lambda_diloco_optimizer_reconciliation_from_paths,
        write_lambda_diloco_optimizer_reconciliation,
    )
    from decodilo.lambda_cloud.diloco_optimizer_success_record import (
        build_lambda_diloco_optimizer_success_record_from_paths,
        write_lambda_diloco_optimizer_success_record,
    )

    success_path = tmp_path / "optimizer-success.json"
    reconciliation_path = tmp_path / "optimizer-reconciliation.json"
    evidence_path = tmp_path / "optimizer-evidence.json"
    closeout_path = tmp_path / "optimizer-closeout.json"
    write_lambda_diloco_optimizer_success_record(
        success_path,
        build_lambda_diloco_optimizer_success_record_from_paths(workdir=workdir),
    )
    write_lambda_diloco_optimizer_reconciliation(
        reconciliation_path,
        build_lambda_diloco_optimizer_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )
    write_lambda_diloco_optimizer_evidence_package(
        evidence_path,
        build_lambda_diloco_optimizer_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )
    write_lambda_diloco_optimizer_closeout(
        closeout_path,
        build_lambda_diloco_optimizer_closeout_from_paths(
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


def write_prior_ssh_history(tmp_path: Path) -> Path:
    path = tmp_path / "ssh-history.json"
    _write_json(
        path,
        {
            "report_schema_version": 1,
            "candidate_region_records": [
                {
                    "milestone": "M057",
                    "selected_candidate": "gpu_1x_a10",
                    "selected_region": "us-east-1",
                    "launch_request_sent": True,
                    "running_verified": True,
                    "host_discovery_status": "FOUND",
                    "ssh_port_reachable": True,
                    "ssh_attempted": True,
                    "remote_command_result": "succeeded",
                    "termination_verified": True,
                    "ssh_ready_success": True,
                    "ssh_port_not_reachable": False,
                },
                {
                    "milestone": "M067R",
                    "selected_candidate": "gpu_1x_h100_sxm5",
                    "selected_region": "us-south-2",
                    "launch_request_sent": True,
                    "running_verified": True,
                    "host_discovery_status": "FOUND",
                    "ssh_port_reachable": False,
                    "ssh_attempted": False,
                    "remote_command_result": "not_attempted",
                    "termination_verified": True,
                    "ssh_ready_success": False,
                    "ssh_port_not_reachable": True,
                },
            ],
            "candidate_region_summaries": [],
            "ssh_ready_success_count": 1,
            "ssh_port_not_reachable_count": 1,
            "launch_ready": False,
            "launch_allowed": False,
            "billable_action_performed": False,
            "real_mutation_enabled": False,
        },
    )
    return path


def write_learner_syncer_closeout(tmp_path: Path) -> Path:
    path = tmp_path / "learner-syncer-closeout.json"
    write_lambda_learner_syncer_smoke_closeout(
        path,
        LambdaLearnerSyncerSmokeCloseout(
            closeout_status="closed_with_warnings",
            closeout_succeeded=True,
            learner_syncer_smoke_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            artifact_auditable=True,
            artifact_body_persisted=True,
            parsed_summary_persisted=True,
            termination_verified=True,
            final_instance_count=0,
            final_unmanaged_count=0,
            no_internet_install=True,
            no_downloads=True,
            no_real_training=True,
            no_unapproved_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )
    return path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
