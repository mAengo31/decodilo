from decodilo.lambda_cloud.strand_response_loss_control_check import (
    build_lambda_strand_response_loss_control_check,
)


def test_strand_response_loss_controls_pass_with_current_mitigation():
    report = build_lambda_strand_response_loss_control_check()

    assert report.controls_passed is True
    assert report.timeout_seconds == 30.0
    assert report.status_before_parse is True
    assert report.no_auto_launch_retry is True
    assert report.strand_launch_parser_accepts_data_instance_ids is True
    assert report.strand_terminate_empty_2xx_supported is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_timeout_below_30_blocks_controls():
    report = build_lambda_strand_response_loss_control_check(timeout_seconds=10.0)

    assert report.controls_passed is False
    assert "timeout_seconds_below_30" in report.blockers


def test_setup_field_blocks_controls():
    report = build_lambda_strand_response_loss_control_check(
        include_setup_field_in_fixture=True
    )

    assert report.controls_passed is False
    assert "setup_cloud_init_or_user_data_field_present" in report.blockers
