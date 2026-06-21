from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    build_lambda_capacity_aware_retry_policy_from_path,
)


def test_capacity_retry_policy_blocks_same_shape_by_default(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_capacity_aware_retry_policy_from_path(history=paths["history"])

    assert report.no_automatic_retry is True
    assert report.same_shape_retry_blocked is True
    assert report.catalog_candidate_rotation_allowed_for_future_review is True
    assert report.recommendation == "block_same_shape_retry"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_live_availability_can_allow_same_shape_future_review(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_capacity_aware_retry_policy_from_path(
        history=paths["history"],
        live_availability_evidence_present=True,
    )

    assert report.same_shape_retry_blocked is False
    assert (
        report.recommendation
        == "allow_same_shape_future_review_with_live_availability"
    )
