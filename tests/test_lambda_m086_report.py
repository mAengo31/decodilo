from __future__ import annotations

from lambda_m084_helpers import write_prior_ssh_history
from lambda_m086_helpers import make_m085r_workdir, write_m086_integrated_closeout_chain

from decodilo.lambda_cloud.integrated_diloco_artifact_audit import (
    build_lambda_integrated_diloco_artifact_audit_from_paths,
    write_lambda_integrated_diloco_artifact_audit,
)
from decodilo.lambda_cloud.m086_report import build_lambda_m086_report_from_paths
from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    build_lambda_m087r_parameter_fragment_authorization_from_paths,
    write_lambda_m087r_parameter_fragment_authorization,
)
from decodilo.lambda_cloud.m087r_parameter_fragment_runbook_preview import (
    build_lambda_m087r_parameter_fragment_runbook_preview_from_path,
    write_lambda_m087r_parameter_fragment_runbook_preview,
)
from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    LambdaParameterFragmentCommandDiscovery,
    write_lambda_parameter_fragment_command_discovery,
)
from decodilo.lambda_cloud.parameter_fragment_policy import (
    build_lambda_parameter_fragment_policy_from_path,
    write_lambda_parameter_fragment_policy,
)
from decodilo.lambda_cloud.parameter_fragment_readiness import (
    build_lambda_parameter_fragment_readiness_from_path,
    write_lambda_parameter_fragment_readiness,
)
from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    build_lambda_ssh_proven_candidate_history_update_from_paths,
    write_lambda_ssh_proven_candidate_history_update,
)


def test_m086_report_passes_and_blocks_m087r_without_command(tmp_path):
    workdir = make_m085r_workdir(tmp_path)
    integrated_paths = write_m086_integrated_closeout_chain(tmp_path, workdir)
    audit_path = tmp_path / "audit.json"
    history_path = tmp_path / "history-m086.json"
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_integrated_diloco_artifact_audit(
        audit_path,
        build_lambda_integrated_diloco_artifact_audit_from_paths(
            workdir=workdir,
            success_record=integrated_paths["success"],
        ),
    )
    write_lambda_ssh_proven_candidate_history_update(
        history_path,
        build_lambda_ssh_proven_candidate_history_update_from_paths(
            prior_history=write_prior_ssh_history(tmp_path),
            workdir=workdir,
        ),
    )
    write_lambda_parameter_fragment_readiness(
        readiness_path,
        build_lambda_parameter_fragment_readiness_from_path(
            integrated_diloco_closeout=integrated_paths["closeout"],
        ),
    )
    write_lambda_parameter_fragment_command_discovery(
        discovery_path,
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="no_safe_parameter_fragment_command_found",
            blockers=["no_safe_parameter_fragment_command_found"],
        ),
    )
    write_lambda_parameter_fragment_policy(
        policy_path,
        build_lambda_parameter_fragment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m087r_parameter_fragment_authorization(
        authorization_path,
        build_lambda_m087r_parameter_fragment_authorization_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m087r_parameter_fragment_runbook_preview(
        runbook_path,
        build_lambda_m087r_parameter_fragment_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m086_report_from_paths(
        success_record=integrated_paths["success"],
        closeout=integrated_paths["closeout"],
        artifact_audit=audit_path,
        ssh_readiness_history=history_path,
        fragment_readiness=readiness_path,
        fragment_discovery=discovery_path,
        fragment_policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.integrated_success_status == "remote_integrated_diloco_synthetic_success"
    assert report.optimization_fidelity == "integrated_optimizer_protocol_smoke"
    assert report.parameter_fragment_semantics == "not_exercised"
    assert report.gpu_1x_a10_us_west_1_recorded is True
    assert report.parameter_fragment_readiness_status == (
        "ready_for_future_parameter_fragment_planning"
    )
    assert report.m087r_authorization_status == "not_authorized"
    assert "no_safe_parameter_fragment_command_found" in report.m087r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
