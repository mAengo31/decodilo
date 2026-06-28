from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir, write_m086_integrated_closeout_chain

from decodilo.lambda_cloud.parameter_fragment_readiness import (
    build_lambda_parameter_fragment_readiness_from_path,
)


def test_parameter_fragment_readiness_passes_after_integrated_closeout(tmp_path):
    paths = write_m086_integrated_closeout_chain(
        tmp_path,
        make_m085r_workdir(tmp_path),
    )

    report = build_lambda_parameter_fragment_readiness_from_path(
        integrated_diloco_closeout=paths["closeout"],
    )

    assert report.readiness_status == "ready_for_future_parameter_fragment_planning"
    assert report.next_scientific_gap == "parameter_fragment_semantics"
    assert report.no_real_training is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
