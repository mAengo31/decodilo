from __future__ import annotations

from lambda_m078_helpers import make_m077r_workdir, write_m078_closeout_chain

from decodilo.lambda_cloud.synthetic_experiment_closeout import (
    build_lambda_synthetic_experiment_closeout_from_paths,
)


def test_synthetic_experiment_closeout_closes_success_with_warnings(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)

    closeout = build_lambda_synthetic_experiment_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.closeout_succeeded is True
    assert closeout.synthetic_experiment_success is True
    assert closeout.final_instance_count == 0
    assert closeout.final_unmanaged_count == 0
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
