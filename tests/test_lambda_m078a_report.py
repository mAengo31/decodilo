from __future__ import annotations

from lambda_m078_helpers import (
    make_m077r_workdir,
    safe_next_discovery_kwargs,
    write_m078_closeout_chain,
)

from decodilo.lambda_cloud.m078a_report import build_lambda_m078a_report_from_paths
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


def test_m078a_report_passes_when_m079r_future_authorized(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    closeout_paths = write_m078_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_next_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_next_synthetic_experiment_readiness_from_path(
            synthetic_experiment_closeout=closeout_paths["closeout"],
        ),
    )
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(**safe_next_discovery_kwargs()),
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
            synthetic_experiment_closeout=closeout_paths["closeout"],
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

    report = build_lambda_m078a_report_from_paths(
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.learner_syncer_smoke_command_added is True
    assert report.discovery_status == "found_safe_next_synthetic_experiment_command"
    assert report.policy_status == "policy_passed"
    assert (
        report.m079r_authorization_status
        == "authorized_for_future_m079r_next_synthetic_experiment"
    )
    assert (
        report.runbook_preview_status
        == "ready_for_future_m079r_next_synthetic_experiment_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
