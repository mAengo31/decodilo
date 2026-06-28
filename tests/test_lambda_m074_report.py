from lambda_m074_helpers import make_m073r2_workdir, write_m074_closeout_chain

from decodilo.lambda_cloud.m074_report import build_lambda_m074_report_from_paths
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths,
    write_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_runbook_preview import (
    build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path,
    write_lambda_m075r_runtime_protocol_smoke_runbook_preview,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    LambdaRuntimeProtocolSmokeDiscovery,
    write_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    build_lambda_runtime_protocol_smoke_policy_from_path,
    write_lambda_runtime_protocol_smoke_policy,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_readiness import (
    build_lambda_runtime_protocol_smoke_readiness_from_path,
    write_lambda_runtime_protocol_smoke_readiness,
)
from decodilo.lambda_cloud.tiny_smoke_artifact_audit import (
    build_lambda_tiny_smoke_artifact_audit_from_paths,
    write_lambda_tiny_smoke_artifact_audit,
)


def test_m074_report_passes_closeout_and_records_m075r_blocker(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    paths = write_m074_closeout_chain(tmp_path, workdir)
    artifact_path = tmp_path / "artifact-audit.json"
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    auth_path = tmp_path / "auth.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_tiny_smoke_artifact_audit(
        artifact_path,
        build_lambda_tiny_smoke_artifact_audit_from_paths(
            workdir=workdir,
            success_record=paths["success"],
        ),
    )
    write_lambda_runtime_protocol_smoke_readiness(
        readiness_path,
        build_lambda_runtime_protocol_smoke_readiness_from_path(
            tiny_smoke_closeout=paths["closeout"],
        ),
    )
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="no_safe_runtime_protocol_smoke_command_found",
            blockers=["no_safe_runtime_protocol_smoke_command_found"],
        ),
    )
    write_lambda_runtime_protocol_smoke_policy(
        policy_path,
        build_lambda_runtime_protocol_smoke_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m075r_runtime_protocol_smoke_authorization(
        auth_path,
        build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths(
            tiny_smoke_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m075r_runtime_protocol_smoke_runbook_preview(
        runbook_path,
        build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path(
            authorization=auth_path,
        ),
    )

    report = build_lambda_m074_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        artifact_audit=artifact_path,
        runtime_readiness=readiness_path,
        runtime_discovery=discovery_path,
        runtime_policy=policy_path,
        authorization=auth_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.closeout_succeeded is True
    assert report.m075r_authorization_status == "not_authorized"
    assert "no_safe_runtime_protocol_smoke_command_found" in report.m075r_blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
