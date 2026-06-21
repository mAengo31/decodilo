from decodilo.lambda_cloud.m034_manual_console_confirmation import (
    build_lambda_m034_manual_console_confirmation,
)


def test_m034_no_confirmation_unresolved():
    report = build_lambda_m034_manual_console_confirmation()

    assert report.confirmation_status == "not_provided"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m034_confirmed_no_visible_instances():
    report = build_lambda_m034_manual_console_confirmation(
        lambda_console_checked=True,
        no_instances_visible=True,
        no_pending_instances_visible=True,
        no_alert_instances_visible=True,
    )

    assert report.confirmation_status == "confirmed_no_visible_instances"
    assert report.no_owned_instance_found is True


def test_m034_manual_termination_requires_redacted_id():
    try:
        build_lambda_m034_manual_console_confirmation(
            lambda_console_checked=True,
            any_instance_terminated_manually=True,
        )
    except ValueError as exc:
        assert "manual termination requires redacted instance id" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("manual termination without id should fail")
