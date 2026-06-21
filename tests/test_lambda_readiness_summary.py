from decodilo.lambda_cloud.launch_blockers import LambdaLaunchBlocker, LambdaLaunchBlockerReport
from decodilo.lambda_cloud.readiness_summary import build_lambda_readiness_summary


def test_lambda_readiness_summary_keeps_real_launch_candidate_false() -> None:
    blockers = LambdaLaunchBlockerReport(
        blockers=[
            LambdaLaunchBlocker(category="launch_code_disabled", message="disabled"),
            LambdaLaunchBlocker(
                category="launch_not_supported_in_current_milestone",
                message="M020",
            ),
        ]
    )

    summary = build_lambda_readiness_summary(
        blocker_report=blockers,
        approval_passed_for_fake_lifecycle=True,
    )

    assert summary.future_fake_launch_lifecycle_candidate is True
    assert summary.future_real_launch_candidate is False
    assert summary.launch_allowed is False
