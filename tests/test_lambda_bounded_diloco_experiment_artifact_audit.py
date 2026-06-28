from __future__ import annotations

from lambda_m090_helpers import make_m089r_workdir, write_m090_bounded_closeout_chain

from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_audit import (
    build_lambda_bounded_diloco_experiment_artifact_audit_from_paths,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_success_record import (
    M089R_BOUNDED_DILOCO_ARTIFACT_SHA256,
)


def test_bounded_diloco_experiment_artifact_audit_passes(tmp_path):
    workdir = make_m089r_workdir(tmp_path)
    paths = write_m090_bounded_closeout_chain(tmp_path, workdir)

    report = build_lambda_bounded_diloco_experiment_artifact_audit_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.artifact_audit_passed is True
    assert report.artifact_sha256 == M089R_BOUNDED_DILOCO_ARTIFACT_SHA256
    assert report.safe_json_body_persisted is True
    assert report.parsed_summary_persisted is True
    assert report.optimization_fidelity == "bounded_synthetic_diloco_experiment"
    assert report.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.full_diloco_training_claimed is False
    assert report.true_model_fragment_claimed is False
    assert report.overlap_semantics == "not_exercised"
    assert report.quantization_semantics == "not_exercised"
