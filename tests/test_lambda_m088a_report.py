from __future__ import annotations

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    LambdaBoundedDilocoExperimentCommandDiscovery,
    write_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    build_lambda_bounded_diloco_experiment_policy_from_path,
    write_lambda_bounded_diloco_experiment_policy,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_readiness import (
    LambdaBoundedDilocoExperimentReadiness,
    write_lambda_bounded_diloco_experiment_readiness,
)
from decodilo.lambda_cloud.m088a_report import build_lambda_m088a_report_from_paths
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths,
    write_lambda_m089r_bounded_diloco_experiment_authorization,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_runbook_preview import (
    build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path,
    write_lambda_m089r_bounded_diloco_experiment_runbook_preview,
)


def test_m088a_report_passes_when_m089r_future_authorized(tmp_path):
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_bounded_diloco_experiment_readiness(
        readiness_path,
        LambdaBoundedDilocoExperimentReadiness(
            readiness_status=(
                "ready_for_first_bounded_synthetic_diloco_experiment_planning"
            ),
            cloud_lifecycle_ready=True,
            remote_source_dependency_path_ready=True,
            learner_syncer_protocol_ready=True,
            adamw_nesterov_optimizer_semantics_ready=True,
            integrated_protocol_optimizer_ready=True,
            synthetic_parameter_fragment_semantics_ready=True,
        ),
    )
    write_lambda_bounded_diloco_experiment_command_discovery(
        discovery_path,
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="found_safe_bounded_diloco_experiment_command",
            command_category="dev_bounded_diloco_experiment_one_step",
            argv_tokens=[
                "env",
                "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "bounded-diloco-experiment",
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--fragments",
                "2",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
                "--out",
                "/tmp/decodilo-bounded-diloco-experiment.json",
            ],
            timeout_seconds=180,
        ),
    )
    write_lambda_bounded_diloco_experiment_policy(
        policy_path,
        build_lambda_bounded_diloco_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m089r_bounded_diloco_experiment_authorization(
        authorization_path,
        build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m089r_bounded_diloco_experiment_runbook_preview(
        runbook_path,
        build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m088a_report_from_paths(
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.bounded_diloco_experiment_command_added is True
    assert report.discovery_status == "found_safe_bounded_diloco_experiment_command"
    assert report.policy_status == "policy_passed"
    assert (
        report.m089r_authorization_status
        == "authorized_for_future_m089r_bounded_diloco_experiment"
    )
    assert (
        report.runbook_preview_status
        == "ready_for_future_m089r_bounded_diloco_experiment_review"
    )
    assert report.bounded_experiment_status == "dev_bounded_diloco_experiment_one_step"
    assert report.learners == 1
    assert report.sync_rounds == 1
    assert report.fragments == 2
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.max_steps == 1
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
