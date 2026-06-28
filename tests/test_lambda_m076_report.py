from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.first_synthetic_experiment_discovery import (
    LambdaFirstSyntheticExperimentDiscovery,
    write_lambda_first_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.first_synthetic_experiment_policy import (
    build_lambda_first_synthetic_experiment_policy_from_path,
    write_lambda_first_synthetic_experiment_policy,
)
from decodilo.lambda_cloud.first_synthetic_experiment_readiness import (
    build_lambda_first_synthetic_experiment_readiness_from_path,
    write_lambda_first_synthetic_experiment_readiness,
)
from decodilo.lambda_cloud.m076_report import build_lambda_m076_report_from_paths
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_authorization import (
    build_lambda_m077r_first_synthetic_experiment_authorization_from_paths,
    write_lambda_m077r_first_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_runbook_preview import (
    build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path,
    write_lambda_m077r_first_synthetic_experiment_runbook_preview,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_audit import (
    build_lambda_runtime_smoke_artifact_audit_from_paths,
    write_lambda_runtime_smoke_artifact_audit,
)


def test_m076_report_passes_closeout_and_records_m077r_blocker(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)
    audit_path = tmp_path / "artifact-audit.json"
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    auth_path = tmp_path / "auth.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_runtime_smoke_artifact_audit(
        audit_path,
        build_lambda_runtime_smoke_artifact_audit_from_paths(
            workdir=workdir,
            success_record=paths["success"],
        ),
    )
    write_lambda_first_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_first_synthetic_experiment_readiness_from_path(
            runtime_smoke_closeout=paths["closeout"],
        ),
    )
    write_lambda_first_synthetic_experiment_discovery(
        discovery_path,
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            blockers=["no_safe_first_synthetic_experiment_command_found"],
        ),
    )
    write_lambda_first_synthetic_experiment_policy(
        policy_path,
        build_lambda_first_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m077r_first_synthetic_experiment_authorization(
        auth_path,
        build_lambda_m077r_first_synthetic_experiment_authorization_from_paths(
            runtime_smoke_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m077r_first_synthetic_experiment_runbook_preview(
        runbook_path,
        build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path(
            authorization=auth_path,
        ),
    )

    report = build_lambda_m076_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        artifact_audit=audit_path,
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=auth_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.closeout_succeeded is True
    assert report.m077r_authorization_status == "not_authorized"
    assert "no_safe_first_synthetic_experiment_command_found" in report.m077r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
