from __future__ import annotations

from lambda_m090_helpers import make_m089r_workdir, write_m090_bounded_closeout_chain

from decodilo.lambda_cloud.bounded_diloco_experiment_closeout import (
    build_lambda_bounded_diloco_experiment_closeout_from_paths,
)


def test_bounded_diloco_experiment_closeout_succeeds(tmp_path):
    paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )

    report = build_lambda_bounded_diloco_experiment_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert report.closeout_succeeded is True
    assert report.closeout_status in {"closed_success", "closed_with_warnings"}
    assert report.bounded_diloco_experiment_success is True
    assert report.bounded_experiment_semantics_confirmed is True
    assert report.historical_billable_action_performed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
