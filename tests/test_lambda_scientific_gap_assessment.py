from __future__ import annotations

from lambda_m090_helpers import make_m089r_workdir, write_m090_bounded_closeout_chain

from decodilo.lambda_cloud.scientific_gap_assessment import (
    build_lambda_scientific_gap_assessment_from_path,
)


def test_scientific_gap_assessment_records_remaining_gaps(tmp_path):
    paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )

    report = build_lambda_scientific_gap_assessment_from_path(
        bounded_artifact_audit=paths["audit"],
    )

    assert report.assessment_status == "scientific_gaps_assessed"
    assert report.real_model_training_done is False
    assert report.true_model_layer_parameter_fragments_done is False
    assert report.communication_computation_overlap_done is False
    assert report.quantized_communication_done is False
    assert "paper_scale_diloco_comparison_not_done" in report.remaining_gaps
    assert report.launch_ready is False
    assert report.launch_allowed is False
