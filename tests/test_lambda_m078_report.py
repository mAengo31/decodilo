from __future__ import annotations

from lambda_m078_helpers import make_m077r_workdir, write_m078_closeout_chain

from decodilo.lambda_cloud.m078_report import build_lambda_m078_report_from_paths
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    build_lambda_m079r_next_synthetic_experiment_authorization_from_paths,
    write_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_runbook_preview import (
    build_lambda_m079r_next_synthetic_experiment_runbook_preview_from_path,
    write_lambda_m079r_next_synthetic_experiment_runbook_preview,
)
from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    LambdaNextSyntheticExperimentDiscovery,
    write_lambda_next_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.next_synthetic_experiment_policy import (
    build_lambda_next_synthetic_experiment_policy_from_path,
    write_lambda_next_synthetic_experiment_policy,
)
from decodilo.lambda_cloud.next_synthetic_experiment_readiness import (
    build_lambda_next_synthetic_experiment_readiness_from_path,
    write_lambda_next_synthetic_experiment_readiness,
)
from decodilo.lambda_cloud.synthetic_experiment_artifact_audit import (
    build_lambda_synthetic_experiment_artifact_audit_from_paths,
    write_lambda_synthetic_experiment_artifact_audit,
)


def test_m078_report_passes_closeout_and_blocks_m079r_without_command(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)
    artifact_audit_path = tmp_path / "artifact-audit.json"
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_synthetic_experiment_artifact_audit(
        artifact_audit_path,
        build_lambda_synthetic_experiment_artifact_audit_from_paths(
            workdir=workdir,
            success_record=paths["success"],
        ),
    )
    write_lambda_next_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_next_synthetic_experiment_readiness_from_path(
            synthetic_experiment_closeout=paths["closeout"],
        ),
    )
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(
            discovery_status="no_safe_next_synthetic_experiment_command_found",
            blockers=["no_safe_next_synthetic_experiment_command_found"],
        ),
    )
    write_lambda_next_synthetic_experiment_policy(
        policy_path,
        build_lambda_next_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m079r_next_synthetic_experiment_authorization(
        authorization_path,
        build_lambda_m079r_next_synthetic_experiment_authorization_from_paths(
            synthetic_experiment_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m079r_next_synthetic_experiment_runbook_preview(
        runbook_path,
        build_lambda_m079r_next_synthetic_experiment_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m078_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        artifact_audit=artifact_audit_path,
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.synthetic_experiment_success_status == (
        "first_remote_synthetic_experiment_success"
    )
    assert report.m079r_authorization_status == "not_authorized"
    assert "no_safe_next_synthetic_experiment_command_found" in report.m079r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
