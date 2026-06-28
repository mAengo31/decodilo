from __future__ import annotations

from lambda_m072_helpers import make_m071r_workdir

from decodilo.lambda_cloud.first_experiment_reconciliation import (
    build_lambda_first_experiment_reconciliation_from_paths,
)
from decodilo.lambda_cloud.first_experiment_success_record import (
    build_lambda_first_experiment_success_record_from_paths,
    write_lambda_first_experiment_success_record,
)


def test_first_experiment_reconciliation_passes_clean_fixture(tmp_path):
    workdir = make_m071r_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    write_lambda_first_experiment_success_record(
        success_path,
        build_lambda_first_experiment_success_record_from_paths(workdir=workdir),
    )

    report = build_lambda_first_experiment_reconciliation_from_paths(
        workdir=workdir,
        success_record=success_path,
    )

    assert report.reconciliation_passed is True
    assert report.final_instance_count == 0
    assert report.no_training is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_first_experiment_reconciliation_blocks_running_instance(tmp_path):
    workdir = make_m071r_workdir(tmp_path, final_instance_count=1)
    success_path = tmp_path / "success.json"
    write_lambda_first_experiment_success_record(
        success_path,
        build_lambda_first_experiment_success_record_from_paths(workdir=workdir),
    )

    report = build_lambda_first_experiment_reconciliation_from_paths(
        workdir=workdir,
        success_record=success_path,
    )

    assert report.reconciliation_passed is False
    assert "success_record_not_success" in report.errors
