from __future__ import annotations

from lambda_m088_helpers import make_m087r_workdir, write_m088_parameter_fragment_closeout_chain

from decodilo.lambda_cloud.parameter_fragment_artifact_audit import (
    build_lambda_parameter_fragment_artifact_audit_from_paths,
)
from decodilo.lambda_cloud.parameter_fragment_success_record import (
    M087R_PARAMETER_FRAGMENT_ARTIFACT_SHA256,
)


def test_parameter_fragment_artifact_audit_preserves_semantic_boundaries(tmp_path):
    workdir = make_m087r_workdir(tmp_path)
    paths = write_m088_parameter_fragment_closeout_chain(tmp_path, workdir)

    report = build_lambda_parameter_fragment_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.artifact_audit_passed is True
    assert report.artifact_sha256 == M087R_PARAMETER_FRAGMENT_ARTIFACT_SHA256
    assert report.safe_json_body_persisted is True
    assert report.parsed_summary_persisted is True
    assert report.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.fragment_count == 2
    assert report.max_abs_error == 0.0
    assert report.overlap_semantics == "not_exercised"
    assert report.quantization_semantics == "not_exercised"
    assert report.launch_ready is False
    assert report.launch_allowed is False
