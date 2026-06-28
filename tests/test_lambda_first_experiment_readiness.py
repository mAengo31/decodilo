from __future__ import annotations

from decodilo.lambda_cloud.first_experiment_readiness import (
    build_lambda_first_experiment_readiness_from_path,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_closeout import (
    LambdaRemoteDecodiloVSliceCloseout,
    write_lambda_remote_decodilo_vslice_closeout,
)


def test_first_experiment_readiness_from_successful_closeout(tmp_path):
    closeout_path = tmp_path / "closeout.json"
    write_lambda_remote_decodilo_vslice_closeout(
        closeout_path,
        LambdaRemoteDecodiloVSliceCloseout(
            closeout_status="closed_success",
            closeout_succeeded=True,
            remote_decodilo_vslice_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            termination_verified=True,
            final_instance_count=0,
            final_unmanaged_count=0,
            no_internet_install=True,
            no_downloads=True,
            no_training=True,
            no_extra_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )

    report = build_lambda_first_experiment_readiness_from_path(closeout=closeout_path)

    assert report.readiness_status == "ready_for_future_first_experiment_planning"
    assert report.decodilo_cli_ready is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
