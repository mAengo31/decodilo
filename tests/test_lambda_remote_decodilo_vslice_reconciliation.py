from __future__ import annotations

from lambda_m070_helpers import make_m069r_workdir

from decodilo.lambda_cloud.remote_decodilo_vslice_reconciliation import (
    build_lambda_remote_decodilo_vslice_reconciliation_from_paths,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    build_lambda_remote_decodilo_vslice_success_record_from_paths,
    write_lambda_remote_decodilo_vslice_success_record,
)


def test_clean_remote_decodilo_reconciliation_passes(tmp_path):
    workdir = make_m069r_workdir(tmp_path)
    record_path = tmp_path / "success.json"
    write_lambda_remote_decodilo_vslice_success_record(
        record_path,
        build_lambda_remote_decodilo_vslice_success_record_from_paths(workdir=workdir),
    )

    report = build_lambda_remote_decodilo_vslice_reconciliation_from_paths(
        workdir=workdir,
        success_record=record_path,
    )

    assert report.reconciliation_passed is True
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False
