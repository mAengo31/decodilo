from __future__ import annotations

from lambda_m072_helpers import make_m071r_workdir

from decodilo.lambda_cloud.first_experiment_success_record import (
    build_lambda_first_experiment_success_record_from_paths,
)


def test_m071r_fixture_produces_first_experiment_success(tmp_path):
    record = build_lambda_first_experiment_success_record_from_paths(
        workdir=make_m071r_workdir(tmp_path),
    )

    assert record.status == "first_experiment_runtime_success"
    assert record.first_experiment_command_passed is True
    assert record.ci_profile_report_artifact_created is True
    assert record.artifact_secret_scan_passed is True
    assert record.launch_ready is False
    assert record.launch_allowed is False
    assert record.billable_action_performed is False
    assert record.historical_billable_action_performed is True


def test_training_attempt_prevents_first_experiment_success(tmp_path):
    record = build_lambda_first_experiment_success_record_from_paths(
        workdir=make_m071r_workdir(tmp_path, training_attempted=True),
    )

    assert record.status != "first_experiment_runtime_success"
    assert "training_detected" in record.blockers
