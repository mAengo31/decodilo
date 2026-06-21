from __future__ import annotations

import json
from pathlib import Path

from lambda_m047_helpers import SUCCESS_REGION, SUCCESS_SHAPE, write_m047_inputs

from decodilo.lambda_cloud.api_models import LambdaInstance
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report
from decodilo.lambda_cloud.m052_report import (
    build_lambda_m052_report_from_paths,
    write_lambda_m052_report,
)
from decodilo.lambda_cloud.m053_next_step_decision import (
    build_lambda_m053_next_step_decision_from_paths,
    write_lambda_m053_next_step_decision,
)
from decodilo.lambda_cloud.metadata_bootstrap_closeout import (
    build_lambda_metadata_bootstrap_closeout_from_paths,
    write_lambda_metadata_bootstrap_closeout,
)
from decodilo.lambda_cloud.metadata_bootstrap_evidence_package import (
    build_lambda_metadata_bootstrap_evidence_package_from_paths,
    write_lambda_metadata_bootstrap_evidence_package,
)
from decodilo.lambda_cloud.metadata_bootstrap_lifecycle_comparison import (
    build_lambda_metadata_bootstrap_lifecycle_comparison_from_paths,
    write_lambda_metadata_bootstrap_lifecycle_comparison,
)
from decodilo.lambda_cloud.metadata_bootstrap_reconciliation import (
    build_lambda_metadata_bootstrap_reconciliation_from_paths,
    write_lambda_metadata_bootstrap_reconciliation,
)
from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    build_lambda_metadata_bootstrap_success_record_from_paths,
    write_lambda_metadata_bootstrap_success_record,
)
from decodilo.lambda_cloud.no_remote_execution_attestation import (
    build_lambda_no_remote_execution_attestation_from_paths,
    write_lambda_no_remote_execution_attestation,
)
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport
from decodilo.lambda_cloud.remote_bootstrap_strategy_update import (
    build_lambda_remote_bootstrap_strategy_update_from_paths,
    write_lambda_remote_bootstrap_strategy_update,
)


def write_m051b_workdir(
    base: Path,
    *,
    ssh_attempted: bool = False,
    remote_command_attempted: bool = False,
    package_install_attempted: bool = False,
    training_attempted: bool = False,
    termination_verified: bool = True,
    final_instance_count: int = 0,
    unmanaged_count: int = 0,
) -> dict[str, Path]:
    workdir = base / "m051b-workdir"
    workdir.mkdir(parents=True)
    report = LambdaM029Report(
        run_id="lambda-m051-metadata-bootstrap",
        real_lambda_api_used=True,
        launch_request_sent=True,
        launch_response_received=True,
        owned_instance_id_redacted="de7cc1...979c",
        readonly_verify_running_result="running",
        termination_request_sent=True,
        termination_response_received=termination_verified,
        readonly_verify_terminated_result=(
            "terminated" if termination_verified else "running"
        ),
        termination_verified=termination_verified,
        manual_review_required=not termination_verified,
        mutating_operations=2,
        billable_action_performed=True,
        estimated_spend=0.04264795472566038,
        elapsed_seconds=6.8787023751065135,
        launch_response_http_status=200,
        launch_response_content_type="application/json",
        launch_response_body_size_bytes=63,
        launch_response_classification="success_json",
        termination_response_http_status=200 if termination_verified else None,
        termination_response_content_type=(
            "application/json" if termination_verified else None
        ),
        termination_response_body_size_bytes=652 if termination_verified else None,
        termination_response_classification=(
            "success_json" if termination_verified else None
        ),
        metadata_bootstrap_path_used=True,
        metadata_only=True,
        metadata_collected={
            "instance_type": SUCCESS_SHAPE,
            "metadata_only": True,
            "region": SUCCESS_REGION,
            "source": "lambda_provider_api",
        },
        selected_shape=SUCCESS_SHAPE,
        selected_candidate=SUCCESS_SHAPE,
        selected_region=SUCCESS_REGION,
        selected_ssh_key_hash="sha256:e8bd9b2e6fc17b09",
        ssh_attempted=ssh_attempted,
        remote_command_attempted=remote_command_attempted,
        package_install_attempted=package_install_attempted,
        training_attempted=training_attempted,
        response_capture_active=True,
        status_before_parse=True,
        no_auto_launch_retry=True,
    )
    (workdir / "report.json").write_text(report.to_json(), encoding="utf-8")
    (workdir / "journal.jsonl").write_text(
        json.dumps({"event": "launch"}) + "\n"
        + json.dumps({"event": "terminate"}) + "\n",
        encoding="utf-8",
    )
    (workdir / "ledger.json").write_text(
        json.dumps({"owned_instance_id_redacted": "de7cc1...979c"}, indent=2) + "\n",
        encoding="utf-8",
    )
    spend = LambdaM029SpendAuditReport(
        estimated_hourly_cost=100.0,
        actual_elapsed_seconds=6.8787023751065135,
        estimated_spend=0.19107506597518092,
        budget_exceeded=False,
        runtime_exceeded=False,
        billable_action_performed=True,
        launch_request_sent=True,
        terminate_request_sent=True,
        termination_verified=termination_verified,
    )
    (workdir / "spend-audit.json").write_text(spend.to_json(), encoding="utf-8")
    instances = [
        LambdaInstance(instance_id="leftover", name="leftover", status="running")
        for _ in range(final_instance_count)
    ]
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        instances=instances,
        unmanaged_instances=[f"unmanaged-{index}" for index in range(unmanaged_count)],
        secret_redacted=True,
    )
    post_discovery = base / "post-m051b-discovery.json"
    write_lambda_live_discovery_report(post_discovery, discovery)
    return {"workdir": workdir, "post_discovery": post_discovery}


def write_m052_inputs(base: Path) -> dict[str, Path]:
    paths = write_m051b_workdir(base)
    paths.update(
        {
            "success": base / "metadata-success.json",
            "reconciliation": base / "metadata-reconciliation.json",
            "evidence": base / "metadata-evidence.json",
            "closeout": base / "metadata-closeout.json",
            "attestation": base / "no-remote-attestation.json",
            "comparison": base / "comparison.json",
            "strategy": base / "strategy.json",
            "decision": base / "decision.json",
            "m052": base / "m052.json",
        }
    )
    success = build_lambda_metadata_bootstrap_success_record_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_metadata_bootstrap_success_record(paths["success"], success)
    reconciliation = build_lambda_metadata_bootstrap_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=paths["success"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_metadata_bootstrap_reconciliation(
        paths["reconciliation"],
        reconciliation,
    )
    evidence = build_lambda_metadata_bootstrap_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        metadata_plan=paths["workdir"] / "report.json",
        execution_gate=paths["workdir"] / "report.json",
        no_mutation_no_ssh_audit=paths["workdir"] / "report.json",
        reviewer_bridge=paths["workdir"] / "report.json",
        arming_gate=paths["workdir"] / "report.json",
        m050_report=paths["workdir"] / "report.json",
    )
    write_lambda_metadata_bootstrap_evidence_package(paths["evidence"], evidence)
    closeout = build_lambda_metadata_bootstrap_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )
    write_lambda_metadata_bootstrap_closeout(paths["closeout"], closeout)
    attestation = build_lambda_no_remote_execution_attestation_from_paths(
        workdir=paths["workdir"],
    )
    write_lambda_no_remote_execution_attestation(paths["attestation"], attestation)
    lifecycle = write_m047_inputs(base / "m047")
    paths["lifecycle_success"] = lifecycle["success"]
    paths["lifecycle_closeout"] = lifecycle["closeout"]
    comparison = build_lambda_metadata_bootstrap_lifecycle_comparison_from_paths(
        lifecycle_closeout=paths["lifecycle_closeout"],
        metadata_closeout=paths["closeout"],
        lifecycle_success_record=paths["lifecycle_success"],
        metadata_success_record=paths["success"],
    )
    write_lambda_metadata_bootstrap_lifecycle_comparison(
        paths["comparison"],
        comparison,
    )
    strategy = build_lambda_remote_bootstrap_strategy_update_from_paths(
        metadata_closeout=paths["closeout"],
    )
    write_lambda_remote_bootstrap_strategy_update(paths["strategy"], strategy)
    decision = build_lambda_m053_next_step_decision_from_paths(
        metadata_closeout=paths["closeout"],
        strategy_update=paths["strategy"],
    )
    write_lambda_m053_next_step_decision(paths["decision"], decision)
    report = build_lambda_m052_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        no_remote_execution_attestation=paths["attestation"],
        comparison=paths["comparison"],
        strategy_update=paths["strategy"],
        decision=paths["decision"],
    )
    write_lambda_m052_report(paths["m052"], report)
    return paths
