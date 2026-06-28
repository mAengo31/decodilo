from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir, write_m080_closeout_chain

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    LambdaDilocoSyntheticCommandDiscovery,
    write_lambda_diloco_synthetic_command_discovery,
)
from decodilo.lambda_cloud.diloco_synthetic_policy import (
    build_lambda_diloco_synthetic_policy_from_path,
    write_lambda_diloco_synthetic_policy,
)
from decodilo.lambda_cloud.diloco_synthetic_readiness import (
    build_lambda_diloco_synthetic_readiness_from_path,
    write_lambda_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.learner_syncer_smoke_artifact_audit import (
    build_lambda_learner_syncer_smoke_artifact_audit_from_paths,
    write_lambda_learner_syncer_smoke_artifact_audit,
)
from decodilo.lambda_cloud.m080_report import build_lambda_m080_report_from_paths
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    build_lambda_m081r_diloco_synthetic_authorization_from_paths,
    write_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_runbook_preview import (
    build_lambda_m081r_diloco_synthetic_runbook_preview_from_path,
    write_lambda_m081r_diloco_synthetic_runbook_preview,
)


def test_m080_report_passes_closeout_and_blocks_m081r_without_command(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)
    artifact_audit_path = tmp_path / "artifact-audit.json"
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_learner_syncer_smoke_artifact_audit(
        artifact_audit_path,
        build_lambda_learner_syncer_smoke_artifact_audit_from_paths(
            workdir=workdir,
            success_record=paths["success"],
        ),
    )
    write_lambda_diloco_synthetic_readiness(
        readiness_path,
        build_lambda_diloco_synthetic_readiness_from_path(
            learner_syncer_closeout=paths["closeout"],
        ),
    )
    write_lambda_diloco_synthetic_command_discovery(
        discovery_path,
        LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="no_safe_diloco_synthetic_command_found",
            blockers=["no_safe_diloco_synthetic_command_found"],
        ),
    )
    write_lambda_diloco_synthetic_policy(
        policy_path,
        build_lambda_diloco_synthetic_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m081r_diloco_synthetic_authorization(
        authorization_path,
        build_lambda_m081r_diloco_synthetic_authorization_from_paths(
            learner_syncer_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m081r_diloco_synthetic_runbook_preview(
        runbook_path,
        build_lambda_m081r_diloco_synthetic_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m080_report_from_paths(
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
    assert report.learner_syncer_smoke_success_status == (
        "remote_learner_syncer_smoke_success"
    )
    assert report.m081r_authorization_status == "not_authorized"
    assert "no_safe_diloco_synthetic_command_found" in report.m081r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
