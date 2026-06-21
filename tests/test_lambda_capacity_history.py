from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.capacity_history import (
    build_lambda_capacity_history_from_paths,
)


def test_capacity_history_detects_repeated_same_shape_errors(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = build_lambda_capacity_history_from_paths(
        latest_closeout=paths["latest_closeout"],
        previous_closeout=paths["closeout"],
    )

    assert report.attempts_analyzed == 2
    assert report.capacity_error_count == 2
    assert report.repeated_capacity_error_detected is True
    assert report.shapes_with_capacity_errors == ["gpu_1x_h100_pcie"]
    assert report.same_shape_retry_recommended is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_history_no_owned_instance_means_no_termination_required(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = build_lambda_capacity_history_from_paths(
        latest_closeout=paths["latest_closeout"],
        previous_closeout=paths["closeout"],
    )

    assert all(not attempt.owned_instance_created for attempt in report.attempts)
    assert all(not attempt.termination_required for attempt in report.attempts)
