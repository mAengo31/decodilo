from __future__ import annotations

import json

from lambda_m081s_helpers import (
    diloco_success_artifact,
    make_m081r_artifact_capture_blocked_workdir,
    write_m081r_manifest,
)

from decodilo.lambda_cloud.diloco_artifact_parser import (
    parse_diloco_artifact_file,
    write_diloco_artifact_parser_report,
)
from decodilo.lambda_cloud.diloco_smoke_attempt_closeout import (
    build_lambda_diloco_smoke_attempt_closeout_from_paths,
    write_lambda_diloco_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_authorization import (
    build_lambda_m081r2_diloco_synthetic_authorization_from_paths,
    write_lambda_m081r2_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_runbook_preview import (
    build_lambda_m081r2_diloco_synthetic_runbook_preview_from_paths,
    write_lambda_m081r2_diloco_synthetic_runbook_preview,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    LambdaM081RDilocoSyntheticAuthorization,
    write_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081s_report import build_lambda_m081s_report_from_paths
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    build_lambda_remote_vslice_manifest_artifact_policy_from_path,
    write_lambda_remote_vslice_manifest_artifact_policy,
)


def test_m081s_report_passes_when_retry_artifacts_are_ready(tmp_path):
    closeout_path = tmp_path / "closeout.json"
    policy_path = tmp_path / "policy.json"
    parser_path = tmp_path / "parser.json"
    previous_path = tmp_path / "previous.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps(diloco_success_artifact()), encoding="utf-8")
    write_lambda_diloco_smoke_attempt_closeout(
        closeout_path,
        build_lambda_diloco_smoke_attempt_closeout_from_paths(
            workdir=make_m081r_artifact_capture_blocked_workdir(tmp_path),
        ),
    )
    write_lambda_remote_vslice_manifest_artifact_policy(
        policy_path,
        build_lambda_remote_vslice_manifest_artifact_policy_from_path(
            manifest=write_m081r_manifest(tmp_path / "manifest.json"),
        ),
    )
    write_diloco_artifact_parser_report(
        parser_path,
        parse_diloco_artifact_file(
            artifact_path=fixture,
            policy=policy_path,
        ),
    )
    write_lambda_m081r_diloco_synthetic_authorization(
        previous_path,
        LambdaM081RDilocoSyntheticAuthorization(
            authorization_status="authorized_for_future_m081r_diloco_synthetic_experiment",
            command_category="dev_diloco_smoke_one_step",
        ),
    )
    write_lambda_m081r2_diloco_synthetic_authorization(
        authorization_path,
        build_lambda_m081r2_diloco_synthetic_authorization_from_paths(
            attempt_closeout=closeout_path,
            manifest_artifact_policy=policy_path,
            previous_authorization=previous_path,
        ),
    )
    write_lambda_m081r2_diloco_synthetic_runbook_preview(
        runbook_path,
        build_lambda_m081r2_diloco_synthetic_runbook_preview_from_paths(
            authorization=authorization_path,
            manifest_artifact_policy=policy_path,
        ),
    )

    report = build_lambda_m081s_report_from_paths(
        attempt_closeout=closeout_path,
        manifest_artifact_policy=policy_path,
        parser_fixture_report=parser_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.command_passed is True
    assert report.artifact_capture_blocked is True
    assert report.manifest_declared_artifact_policy_fixed is True
    assert (
        report.m081r2_authorization_status
        == "authorized_for_future_m081r2_diloco_synthetic_retry"
    )
    assert "/tmp/decodilo-diloco-smoke.json" in report.supported_declared_paths
    assert "/tmp/decodilo-learner-syncer-smoke.json" in report.supported_declared_paths
    assert "/tmp/decodilo-runtime-smoke.json" in report.supported_declared_paths
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
