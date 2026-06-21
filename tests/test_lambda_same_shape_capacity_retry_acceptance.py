from decodilo.lambda_cloud.same_shape_capacity_retry_acceptance import (
    build_lambda_same_shape_capacity_retry_acceptance,
)


def test_same_shape_capacity_retry_acceptance_complete():
    report = build_lambda_same_shape_capacity_retry_acceptance(
        shape="gpu_1x_h100_pcie",
        acknowledge_all=True,
    )

    assert (
        report.acceptance_status
        == "accepted_for_future_same_shape_capacity_retry_review"
    )
    assert report.acceptance_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_same_shape_capacity_retry_acceptance_missing_ack_blocks():
    report = build_lambda_same_shape_capacity_retry_acceptance(
        shape="gpu_1x_h100_pcie"
    )

    assert report.acceptance_status == "not_provided"
    assert report.acceptance_complete is False
    assert any(item.startswith("missing_acknowledgement:") for item in report.blockers)


def test_same_shape_capacity_retry_acceptance_declined():
    report = build_lambda_same_shape_capacity_retry_acceptance(
        shape="gpu_1x_h100_pcie",
        decline=True,
    )

    assert report.acceptance_status == "declined"
    assert report.acceptance_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
