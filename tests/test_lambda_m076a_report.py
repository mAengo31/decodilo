from __future__ import annotations

from decodilo.lambda_cloud.first_synthetic_experiment_discovery import (
    LambdaFirstSyntheticExperimentDiscovery,
    write_lambda_first_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.first_synthetic_experiment_policy import (
    build_lambda_first_synthetic_experiment_policy_from_path,
    write_lambda_first_synthetic_experiment_policy,
)
from decodilo.lambda_cloud.m076a_report import build_lambda_m076a_report_from_paths
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_authorization import (
    LambdaM077RFirstSyntheticExperimentAuthorization,
    write_lambda_m077r_first_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_runbook_preview import (
    build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path,
    write_lambda_m077r_first_synthetic_experiment_runbook_preview,
)


def test_m076a_report_passes_when_m077r_future_authorized(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_first_synthetic_experiment_discovery(
        discovery_path,
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="found_safe_first_synthetic_experiment_command",
            command_category="dev_synthetic_experiment_one_step",
            argv_tokens=[
                "env",
                "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "synthetic-experiment",
                "--synthetic",
                "--max-steps",
                "1",
                "--out",
                "/tmp/decodilo-synthetic-experiment.json",
            ],
            local_introspection_passed=True,
            timeout_seconds=120,
        ),
    )
    write_lambda_first_synthetic_experiment_policy(
        policy_path,
        build_lambda_first_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m077r_first_synthetic_experiment_authorization(
        authorization_path,
        LambdaM077RFirstSyntheticExperimentAuthorization(
            authorization_status=(
                "authorized_for_future_m077r_first_synthetic_experiment"
            ),
            command_category="dev_synthetic_experiment_one_step",
        ),
    )
    write_lambda_m077r_first_synthetic_experiment_runbook_preview(
        runbook_path,
        build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m076a_report_from_paths(
        command_discovery=discovery_path,
        policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.synthetic_experiment_command_added is True
    assert (
        report.discovery_status == "found_safe_first_synthetic_experiment_command"
    )
    assert report.policy_status == "policy_passed"
    assert (
        report.m077r_authorization_status
        == "authorized_for_future_m077r_first_synthetic_experiment"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
