from lambda_m035_helpers import attempt_history


def test_three_attempts_represented_and_closed(tmp_path):
    report = attempt_history(tmp_path)

    assert report.attempts_represented == 3
    assert report.response_loss_count == 3
    assert report.repeated_response_loss_detected is True
    assert report.all_incidents_closed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert "M034C" in report.to_json()


def test_attempt_history_rejects_launch_flags(tmp_path):
    payload = attempt_history(tmp_path).model_dump()
    payload["launch_allowed"] = True

    from decodilo.lambda_cloud.launch_attempt_history import (
        LambdaLaunchAttemptHistoryReport,
    )

    try:
        LambdaLaunchAttemptHistoryReport.model_validate(payload)
    except ValueError as exc:
        assert "cannot enable launch" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("launch_allowed=true should be rejected")
