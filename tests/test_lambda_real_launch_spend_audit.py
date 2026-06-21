from decodilo.lambda_cloud.real_launch_spend_audit import build_m029_spend_audit


def test_real_launch_spend_audit_estimates_and_flags_runtime():
    report = build_m029_spend_audit(
        estimated_hourly_cost=100,
        elapsed_seconds=60,
        launch_request_sent=True,
        terminate_request_sent=True,
        termination_verified=True,
        billable_action_performed=True,
    )

    assert round(report.estimated_spend, 2) == 1.67
    assert report.budget_exceeded is False

    late = build_m029_spend_audit(
        estimated_hourly_cost=100,
        elapsed_seconds=2000,
        launch_request_sent=True,
        terminate_request_sent=False,
        termination_verified=False,
    )

    assert late.runtime_exceeded is True
    assert late.warnings
