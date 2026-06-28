from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain
from lambda_m084_helpers import (
    make_m083r_workdir,
    write_learner_syncer_closeout,
    write_m084_optimizer_closeout_chain,
    write_prior_ssh_history,
)

from decodilo.lambda_cloud.diloco_optimizer_artifact_audit import (
    build_lambda_diloco_optimizer_artifact_audit_from_paths,
    write_lambda_diloco_optimizer_artifact_audit,
)
from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    LambdaIntegratedDilocoCommandDiscovery,
    write_lambda_integrated_diloco_command_discovery,
)
from decodilo.lambda_cloud.integrated_diloco_policy import (
    build_lambda_integrated_diloco_policy_from_path,
    write_lambda_integrated_diloco_policy,
)
from decodilo.lambda_cloud.integrated_diloco_synthetic_readiness import (
    build_lambda_integrated_diloco_synthetic_readiness_from_paths,
    write_lambda_integrated_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.m084_report import build_lambda_m084_report_from_paths
from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    build_lambda_m085r_integrated_diloco_authorization_from_paths,
    write_lambda_m085r_integrated_diloco_authorization,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_runbook_preview import (
    build_lambda_m085r_integrated_diloco_runbook_preview_from_path,
    write_lambda_m085r_integrated_diloco_runbook_preview,
)
from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    build_lambda_ssh_proven_candidate_history_update_from_paths,
    write_lambda_ssh_proven_candidate_history_update,
)


def test_m084_report_passes_and_blocks_m085r_without_command(tmp_path):
    m083r_workdir = make_m083r_workdir(tmp_path)
    optimizer_paths = write_m084_optimizer_closeout_chain(tmp_path, m083r_workdir)
    audit_path = tmp_path / "optimizer-audit.json"
    history_path = tmp_path / "history-m084.json"
    readiness_path = tmp_path / "integrated-readiness.json"
    discovery_path = tmp_path / "integrated-discovery.json"
    policy_path = tmp_path / "integrated-policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_diloco_optimizer_artifact_audit(
        audit_path,
        build_lambda_diloco_optimizer_artifact_audit_from_paths(
            workdir=m083r_workdir,
            success_record=optimizer_paths["success"],
        ),
    )
    write_lambda_ssh_proven_candidate_history_update(
        history_path,
        build_lambda_ssh_proven_candidate_history_update_from_paths(
            prior_history=write_prior_ssh_history(tmp_path),
            workdir=m083r_workdir,
        ),
    )
    diloco_paths = write_m082_closeout_chain(tmp_path, make_m081r2_workdir(tmp_path))
    write_lambda_integrated_diloco_synthetic_readiness(
        readiness_path,
        build_lambda_integrated_diloco_synthetic_readiness_from_paths(
            diloco_synthetic_closeout=diloco_paths["closeout"],
            optimizer_closeout=optimizer_paths["closeout"],
            learner_syncer_closeout=write_learner_syncer_closeout(tmp_path),
        ),
    )
    write_lambda_integrated_diloco_command_discovery(
        discovery_path,
        LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="no_safe_integrated_diloco_command_found",
            blockers=["no_safe_integrated_diloco_command_found"],
        ),
    )
    write_lambda_integrated_diloco_policy(
        policy_path,
        build_lambda_integrated_diloco_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m085r_integrated_diloco_authorization(
        authorization_path,
        build_lambda_m085r_integrated_diloco_authorization_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m085r_integrated_diloco_runbook_preview(
        runbook_path,
        build_lambda_m085r_integrated_diloco_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m084_report_from_paths(
        optimizer_success_record=optimizer_paths["success"],
        optimizer_closeout=optimizer_paths["closeout"],
        optimizer_artifact_audit=audit_path,
        ssh_readiness_history=history_path,
        integrated_readiness=readiness_path,
        integrated_discovery=discovery_path,
        integrated_policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.optimizer_success_status == "remote_diloco_optimizer_smoke_success"
    assert report.optimization_fidelity == "optimizer_semantics_smoke"
    assert report.gpu_1x_a10_us_west_1_recorded is True
    assert report.integrated_readiness_status == (
        "ready_for_future_integrated_diloco_planning"
    )
    assert report.m085r_authorization_status == "not_authorized"
    assert "no_safe_integrated_diloco_command_found" in report.m085r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
