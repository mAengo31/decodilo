from __future__ import annotations

from lambda_m082_helpers import (
    make_m081r2_workdir,
    safe_optimizer_discovery_kwargs,
    write_m082_closeout_chain,
)

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    LambdaDilocoOptimizerCommandDiscovery,
    write_lambda_diloco_optimizer_command_discovery,
)
from decodilo.lambda_cloud.diloco_optimizer_policy import (
    build_lambda_diloco_optimizer_policy_from_path,
    write_lambda_diloco_optimizer_policy,
)
from decodilo.lambda_cloud.diloco_optimizer_readiness import (
    build_lambda_diloco_optimizer_readiness_from_path,
    write_lambda_diloco_optimizer_readiness,
)
from decodilo.lambda_cloud.m082a_report import build_lambda_m082a_report_from_paths
from decodilo.lambda_cloud.m083r_diloco_optimizer_authorization import (
    build_lambda_m083r_diloco_optimizer_authorization_from_paths,
    write_lambda_m083r_diloco_optimizer_authorization,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_runbook_preview import (
    build_lambda_m083r_diloco_optimizer_runbook_preview_from_path,
    write_lambda_m083r_diloco_optimizer_runbook_preview,
)


def test_m082a_report_passes_when_m083r_future_authorized(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_diloco_optimizer_readiness(
        readiness_path,
        build_lambda_diloco_optimizer_readiness_from_path(
            diloco_synthetic_closeout=paths["closeout"],
        ),
    )
    write_lambda_diloco_optimizer_command_discovery(
        discovery_path,
        LambdaDilocoOptimizerCommandDiscovery(**safe_optimizer_discovery_kwargs()),
    )
    write_lambda_diloco_optimizer_policy(
        policy_path,
        build_lambda_diloco_optimizer_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m083r_diloco_optimizer_authorization(
        authorization_path,
        build_lambda_m083r_diloco_optimizer_authorization_from_paths(
            diloco_synthetic_closeout=paths["closeout"],
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m083r_diloco_optimizer_runbook_preview(
        runbook_path,
        build_lambda_m083r_diloco_optimizer_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m082a_report_from_paths(
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.diloco_optimizer_smoke_command_added is True
    assert report.discovery_status == "found_safe_diloco_optimizer_command"
    assert report.policy_status == "policy_passed"
    assert (
        report.m083r_authorization_status
        == "authorized_for_future_m083r_diloco_optimizer_smoke"
    )
    assert report.runbook_preview_status == "ready_for_future_m083r_diloco_optimizer_review"
    assert report.optimizer_fidelity_status == "optimizer_semantics_smoke"
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
