from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    LambdaRemoteVerticalSliceCommandEntry,
    LambdaRemoteVerticalSliceCommandManifest,
    render_lambda_remote_vertical_slice_argv,
    write_lambda_remote_vertical_slice_command_manifest,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_m081r_artifact_capture_blocked_workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / "decodilo-lambda-m081r"
    workdir.mkdir()
    stage_results = [
        {"stage": "decodilo_import_check", "passed": True, "exit_code": 0},
        {"stage": "decodilo_cli_help_check", "passed": True, "exit_code": 0},
        {"stage": "diloco_smoke_command", "passed": True, "exit_code": 0},
    ]
    report = {
        "failed_stage": "experiment_output_artifact_capture",
        "vertical_slice_status": "vertical_slice_failed_at_experiment_output_artifact_capture",
        "source_bundle_upload_succeeded": True,
        "dependency_bundle_upload_succeeded": True,
        "local_dependency_install_succeeded": True,
        "remote_command_stage_results": stage_results,
        "package_install_attempted": False,
        "downloads_attempted": False,
        "training_attempted": False,
        "termination_verified": True,
        "billable_action_performed": True,
        "experiment_output_artifact_path": DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
        "experiment_output_artifact_capture_attempted": True,
        "experiment_output_artifact_content_capture_status": "blocked_undeclared_artifact_path",
        "experiment_output_artifact_exists": False,
        "experiment_output_artifact_sha256": None,
        "experiment_output_artifact_body_persisted": False,
        "experiment_output_artifact_parsed_summary_persisted": False,
        "launch_ready": False,
        "launch_allowed": False,
    }
    evidence = {
        "billable_action_performed": False,
        "experiment_output_artifact_body_persisted": False,
        "experiment_output_artifact_parsed_summary_persisted": False,
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
    write_json(workdir / "spend-audit.json", {"billable_action_performed": True})
    write_json(workdir / "post-discovery-summary.json", post)
    return workdir


def write_m081r_manifest(
    path: Path,
    *,
    out_path: str = DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
) -> Path:
    tokens = [
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
        out_path,
    ]
    entry = LambdaRemoteVerticalSliceCommandEntry(
        stage="diloco_smoke_command",
        exact_command=render_lambda_remote_vertical_slice_argv(tokens),
        argv_tokens=tokens,
        failure_stage_if_nonzero="diloco_smoke_command",
        timeout_seconds=60,
    )
    manifest = LambdaRemoteVerticalSliceCommandManifest(
        milestone="M081R",
        max_remote_commands=1,
        command_entries=[entry],
        dependency_strategy="local_wheelhouse",
    )
    write_lambda_remote_vertical_slice_command_manifest(path, manifest)
    return path


def diloco_success_artifact() -> dict:
    return {
        "diloco_smoke_status": "passed",
        "synthetic": True,
        "learners_requested": 1,
        "sync_rounds_requested": 1,
        "max_steps": 1,
        "learner_count_observed": 1,
        "syncer_role_check_passed": True,
        "learner_syncer_exchange_check_passed": True,
        "update_or_commit_check_passed": True,
        "sync_rounds_completed": 1,
        "global_version_before": 0,
        "global_version_after": 1,
        "synthetic_updates_produced": 1,
        "synthetic_updates_accepted": 1,
        "synthetic_updates_rejected": 0,
        "replay_or_metric_check_passed": True,
        "artifact_or_report_check_passed": True,
        "optimization_fidelity": "diloco_shaped_protocol_only",
        "inner_optimizer_semantics": "synthetic_placeholder",
        "outer_optimizer_semantics": "token_weighted_merge",
        "parameter_fragment_semantics": "not_exercised",
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
