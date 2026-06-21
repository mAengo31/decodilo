from lambda_m040_helpers import write_m040_inputs

from decodilo.lambda_cloud.m040_report import build_lambda_m040_report_from_paths


def test_m040_report_summarizes_capacity_closeout_and_future_review(tmp_path):
    paths = write_m040_inputs(tmp_path)

    report = build_lambda_m040_report_from_paths(
        capacity_closeout=paths["closeout"],
        availability_authorization=paths["authorization"],
        go_no_go=paths["go"],
    )

    assert report.capacity_closeout_status == (
        "closed_capacity_unavailable_no_instance_created"
    )
    assert (
        report.availability_authorization_status
        == "authorized_for_future_availability_first_launch_review"
    )
    assert report.go_no_go_status == "go_for_future_availability_first_launch_review"
    assert report.report_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
