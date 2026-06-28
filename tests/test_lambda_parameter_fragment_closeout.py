from __future__ import annotations

from lambda_m088_helpers import make_m087r_workdir, write_m088_parameter_fragment_closeout_chain

from decodilo.lambda_cloud.parameter_fragment_closeout import (
    build_lambda_parameter_fragment_closeout_from_paths,
)


def test_parameter_fragment_closeout_succeeds_with_warnings(tmp_path):
    paths = write_m088_parameter_fragment_closeout_chain(
        tmp_path,
        make_m087r_workdir(tmp_path),
    )

    report = build_lambda_parameter_fragment_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert report.closeout_succeeded is True
    assert report.closeout_status == "closed_with_warnings"
    assert report.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.overlap_semantics == "not_exercised"
    assert report.quantization_semantics == "not_exercised"
    assert report.launch_ready is False
    assert report.launch_allowed is False
