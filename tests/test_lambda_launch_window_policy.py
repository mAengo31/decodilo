from pydantic import ValidationError

from decodilo.lambda_cloud.launch_window_policy import (
    LambdaLaunchWindowPolicy,
    evaluate_lambda_launch_window_policy,
)


def test_launch_window_policy_passes_design_review_defaults() -> None:
    report = evaluate_lambda_launch_window_policy()

    assert report.policy_passed_for_design_review is True
    assert report.launch_allowed is False


def test_launch_window_rejects_active_window_in_m023() -> None:
    try:
        LambdaLaunchWindowPolicy(window_active=True)
    except ValidationError as exc:
        assert "cannot activate launch" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("launch window activated")
