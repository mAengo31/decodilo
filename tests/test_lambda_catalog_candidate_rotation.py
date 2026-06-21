from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.catalog_candidate_rotation import (
    build_lambda_catalog_candidate_rotation_from_paths,
)


def test_catalog_rotation_excludes_recent_capacity_shape_by_default(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = build_lambda_catalog_candidate_rotation_from_paths(
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        ssh_key_selection=paths["ssh"],
    )

    excluded_shapes = {candidate.shape for candidate in report.excluded_candidates}
    assert "gpu_1x_h100_pcie" in excluded_shapes
    assert report.selected_candidate is not None
    assert report.selected_candidate.shape != "gpu_1x_h100_pcie"
    assert report.selection_status == "selected_alternative_catalog_candidate"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_rotation_can_include_failed_shape_with_operator_override(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = build_lambda_catalog_candidate_rotation_from_paths(
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        ssh_key_selection=paths["ssh"],
        allow_failed_shape_retry=True,
    )

    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_1x_h100_pcie"


def test_catalog_rotation_blocks_missing_ssh_key(tmp_path):
    paths = write_m043_inputs(tmp_path)
    paths["ssh"].write_text(
        paths["ssh"].read_text(encoding="utf-8").replace(
            '"selection_passed": true',
            '"selection_passed": false',
        ),
        encoding="utf-8",
    )

    report = build_lambda_catalog_candidate_rotation_from_paths(
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        ssh_key_selection=paths["ssh"],
    )

    assert "existing_ssh_key_selection_required" in report.blockers
