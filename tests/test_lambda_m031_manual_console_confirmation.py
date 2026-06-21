import pytest

from decodilo.lambda_cloud.m031_manual_console_confirmation import (
    build_lambda_m031_manual_console_confirmation,
)


def test_no_confirmation_is_not_provided():
    report = build_lambda_m031_manual_console_confirmation()

    assert report.confirmation_status == "not_provided"
    assert report.launch_allowed is False


def test_confirmed_no_visible_instances_is_closeout_candidate():
    report = build_lambda_m031_manual_console_confirmation(
        lambda_console_checked=True,
        no_instances_visible=True,
        no_pending_instances_visible=True,
        no_alert_instances_visible=True,
        no_owned_instance_found=True,
    )

    assert report.confirmation_status == "confirmed_no_visible_instances"
    assert report.no_owned_instance_found is True


def test_manual_termination_requires_instance_id():
    with pytest.raises(ValueError):
        build_lambda_m031_manual_console_confirmation(
            lambda_console_checked=True,
            any_instance_terminated_manually=True,
        )


def test_manual_termination_redacts_instance_id():
    report = build_lambda_m031_manual_console_confirmation(
        lambda_console_checked=True,
        any_instance_terminated_manually=True,
        manually_terminated_instance_id="real-instance-abcdef123456",
    )

    assert report.confirmation_status == "confirmed_manual_termination_performed"
    assert report.manually_terminated_instance_id_redacted != "real-instance-abcdef123456"
