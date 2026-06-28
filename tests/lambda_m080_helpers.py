from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.learner_syncer_smoke_success_record import (
    M068W_DEPENDENCY_BUNDLE_SHA256,
    M079R2_LEARNER_SYNCER_ARTIFACT_BYTES,
    M079R2_LEARNER_SYNCER_ARTIFACT_PATH,
    M079R2_LEARNER_SYNCER_ARTIFACT_SHA256,
    M079R2_REQUIRED_STAGES,
    M079R2_SOURCE_BUNDLE_SHA256,
)


def make_m079r2_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "m079r2"
    workdir.mkdir()
    stage_results = [
        {
            "stage": stage,
            "passed": True,
            "exit_code": 0,
            "stdout_truncated": False,
            "stderr_truncated": False,
        }
        for stage in M079R2_REQUIRED_STAGES
    ]
    artifact_body = {
        "learner_syncer_smoke_status": "passed",
        "learner_check_passed": True,
        "syncer_check_passed": True,
        "learner_syncer_exchange_check_passed": True,
        "update_or_commit_check_passed": True,
        "replay_or_metric_check_passed": True,
        "synthetic_steps_completed": 1,
        "synthetic_updates_produced": 1,
        "synthetic_updates_accepted": 1,
        "synthetic_updates_rejected": 0,
        "sync_rounds_completed": 1,
        "useful_synthetic_tokens": 13,
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
        "run_id": "lambda-m079r-next-synthetic-experiment",
        "selected_candidate": "gpu_1x_a10",
        "selected_shape": "gpu_1x_a10",
        "selected_region": "us-east-1",
        "source_bundle_sha256": M079R2_SOURCE_BUNDLE_SHA256,
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
        "experiment_output_artifact_path": M079R2_LEARNER_SYNCER_ARTIFACT_PATH,
        "experiment_output_artifact_bytes": M079R2_LEARNER_SYNCER_ARTIFACT_BYTES,
        "experiment_output_artifact_sha256": M079R2_LEARNER_SYNCER_ARTIFACT_SHA256,
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
        "estimated_spend": 0.09577552637102392,
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
            "estimated_spend": 7.424459408606506,
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


def write_m080_closeout_chain(tmp_path: Path, workdir: Path) -> dict[str, Path]:
    from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
        build_lambda_learner_syncer_smoke_closeout_from_paths,
        write_lambda_learner_syncer_smoke_closeout,
    )
    from decodilo.lambda_cloud.learner_syncer_smoke_evidence_package import (
        build_lambda_learner_syncer_smoke_evidence_package_from_paths,
        write_lambda_learner_syncer_smoke_evidence_package,
    )
    from decodilo.lambda_cloud.learner_syncer_smoke_reconciliation import (
        build_lambda_learner_syncer_smoke_reconciliation_from_paths,
        write_lambda_learner_syncer_smoke_reconciliation,
    )
    from decodilo.lambda_cloud.learner_syncer_smoke_success_record import (
        build_lambda_learner_syncer_smoke_success_record_from_paths,
        write_lambda_learner_syncer_smoke_success_record,
    )

    success_path = tmp_path / "learner-syncer-success.json"
    reconciliation_path = tmp_path / "learner-syncer-reconciliation.json"
    evidence_path = tmp_path / "learner-syncer-evidence.json"
    closeout_path = tmp_path / "learner-syncer-closeout.json"
    write_lambda_learner_syncer_smoke_success_record(
        success_path,
        build_lambda_learner_syncer_smoke_success_record_from_paths(workdir=workdir),
    )
    write_lambda_learner_syncer_smoke_reconciliation(
        reconciliation_path,
        build_lambda_learner_syncer_smoke_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )
    write_lambda_learner_syncer_smoke_evidence_package(
        evidence_path,
        build_lambda_learner_syncer_smoke_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )
    write_lambda_learner_syncer_smoke_closeout(
        closeout_path,
        build_lambda_learner_syncer_smoke_closeout_from_paths(
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


def safe_diloco_discovery_kwargs() -> dict:
    return {
        "discovery_status": "found_safe_diloco_synthetic_command",
        "command_category": "dev_diloco_smoke_one_learner_one_round",
        "argv_tokens": [
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-smoke",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "1",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-diloco-smoke.json",
        ],
        "local_introspection_passed": True,
        "timeout_seconds": 120,
    }


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
