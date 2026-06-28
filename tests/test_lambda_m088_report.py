from __future__ import annotations

from lambda_m084_helpers import write_prior_ssh_history
from lambda_m088_helpers import (
    make_m087r_workdir,
    write_m088_parameter_fragment_closeout_chain,
    write_simple_closeout,
)

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    LambdaBoundedDilocoExperimentCommandDiscovery,
    write_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    build_lambda_bounded_diloco_experiment_policy_from_path,
    write_lambda_bounded_diloco_experiment_policy,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_readiness import (
    build_lambda_bounded_diloco_experiment_readiness_from_path,
    write_lambda_bounded_diloco_experiment_readiness,
)
from decodilo.lambda_cloud.m088_report import build_lambda_m088_report_from_paths
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths,
    write_lambda_m089r_bounded_diloco_experiment_authorization,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_runbook_preview import (
    build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path,
    write_lambda_m089r_bounded_diloco_experiment_runbook_preview,
)
from decodilo.lambda_cloud.parameter_fragment_artifact_audit import (
    build_lambda_parameter_fragment_artifact_audit_from_paths,
    write_lambda_parameter_fragment_artifact_audit,
)
from decodilo.lambda_cloud.scaffold_complete_decision import (
    build_lambda_scaffold_complete_decision_from_paths,
    write_lambda_scaffold_complete_decision,
)
from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    build_lambda_ssh_proven_candidate_history_update_from_paths,
    write_lambda_ssh_proven_candidate_history_update,
)


def test_m088_report_passes_while_m089r_remains_fail_closed(tmp_path):
    workdir = make_m087r_workdir(tmp_path)
    closeout_paths = write_m088_parameter_fragment_closeout_chain(tmp_path, workdir)
    audit_path = tmp_path / "parameter-fragment-audit.json"
    write_lambda_parameter_fragment_artifact_audit(
        audit_path,
        build_lambda_parameter_fragment_artifact_audit_from_paths(
            workdir=workdir,
            success_record=closeout_paths["success"],
        ),
    )
    ssh_history_path = tmp_path / "ssh-history-m088.json"
    write_lambda_ssh_proven_candidate_history_update(
        ssh_history_path,
        build_lambda_ssh_proven_candidate_history_update_from_paths(
            prior_history=write_prior_ssh_history(tmp_path),
            workdir=workdir,
        ),
    )
    scaffold_path = tmp_path / "scaffold-decision.json"
    write_lambda_scaffold_complete_decision(
        scaffold_path,
        build_lambda_scaffold_complete_decision_from_paths(
            runtime_smoke_closeout=write_simple_closeout(tmp_path, "runtime"),
            learner_syncer_closeout=write_simple_closeout(tmp_path, "learner-syncer"),
            diloco_synthetic_closeout=write_simple_closeout(
                tmp_path, "diloco-synthetic"
            ),
            optimizer_closeout=write_simple_closeout(tmp_path, "optimizer"),
            integrated_closeout=write_simple_closeout(tmp_path, "integrated"),
            parameter_fragment_closeout=closeout_paths["closeout"],
        ),
    )
    readiness_path = tmp_path / "bounded-readiness.json"
    write_lambda_bounded_diloco_experiment_readiness(
        readiness_path,
        build_lambda_bounded_diloco_experiment_readiness_from_path(
            scaffold_decision=scaffold_path,
        ),
    )
    discovery_path = tmp_path / "bounded-discovery.json"
    write_lambda_bounded_diloco_experiment_command_discovery(
        discovery_path,
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="no_safe_bounded_diloco_experiment_command_found",
            blockers=["no_safe_bounded_diloco_experiment_command_found"],
        ),
    )
    policy_path = tmp_path / "bounded-policy.json"
    write_lambda_bounded_diloco_experiment_policy(
        policy_path,
        build_lambda_bounded_diloco_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m089r_bounded_diloco_experiment_authorization(
        authorization_path,
        build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    runbook_path = tmp_path / "runbook.json"
    write_lambda_m089r_bounded_diloco_experiment_runbook_preview(
        runbook_path,
        build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m088_report_from_paths(
        parameter_fragment_success_record=closeout_paths["success"],
        parameter_fragment_closeout=closeout_paths["closeout"],
        parameter_fragment_artifact_audit=audit_path,
        ssh_readiness_history=ssh_history_path,
        scaffold_decision=scaffold_path,
        bounded_readiness=readiness_path,
        bounded_discovery=discovery_path,
        bounded_policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.parameter_fragment_closeout_succeeded is True
    assert report.scaffold_status == "scaffold_validation_complete"
    assert (
        report.bounded_discovery_status
        == "no_safe_bounded_diloco_experiment_command_found"
    )
    assert report.m089r_authorization_status == "not_authorized"
    assert "m089r_not_authorized" in report.m089r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
