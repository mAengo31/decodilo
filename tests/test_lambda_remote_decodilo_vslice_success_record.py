from __future__ import annotations

from lambda_m070_helpers import make_m069r_workdir

from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    build_lambda_remote_decodilo_vslice_success_record_from_paths,
)


def test_m069r_fixture_produces_remote_decodilo_success(tmp_path):
    record = build_lambda_remote_decodilo_vslice_success_record_from_paths(
        workdir=make_m069r_workdir(tmp_path),
    )

    assert record.status == "remote_decodilo_vslice_success"
    assert record.decodilo_import_passed is True
    assert record.cli_help_passed is True
    assert record.profile_summary_passed is True
    assert record.ci_profile_smoke_passed is True
    assert record.launch_ready is False
    assert record.launch_allowed is False
    assert record.billable_action_performed is False
    assert record.historical_billable_action_performed is True


def test_training_attempt_prevents_success(tmp_path):
    record = build_lambda_remote_decodilo_vslice_success_record_from_paths(
        workdir=make_m069r_workdir(tmp_path, training_attempted=True),
    )

    assert record.status != "remote_decodilo_vslice_success"
    assert "training_detected" in record.blockers
