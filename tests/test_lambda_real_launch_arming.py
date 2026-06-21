from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
    arm_lambda_m029_from_package,
)


def test_real_launch_arming_complete_and_missing_confirmation_blocks(tmp_path):
    fx = m029_fixture(tmp_path)

    assert fx["arming"].arming_passed is True
    assert fx["token"].arming_succeeded is True
    assert fx["token"].launch_allowed is False

    blocked = arm_lambda_m029_from_package(
        run_id="blocked",
        execute_real_launch=True,
        confirm_billable_action=CONFIRM_BILLABLE_ACTION,
        confirm_terminate_required="wrong",
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        emergency_stop_present=True,
        idempotency_key="key",
        fake_server_mode=True,
    )

    assert blocked.arming_passed is False
    assert any("terminate-required" in item for item in blocked.blockers)


def test_real_launch_arming_token_cannot_be_reused(tmp_path):
    fx = m029_fixture(tmp_path)
    used = fx["token"].mark_used()

    try:
        used.require_unused()
    except ValueError as exc:
        assert "already been used" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("used token should be rejected")

    assert CONFIRM_TERMINATE_REQUIRED
