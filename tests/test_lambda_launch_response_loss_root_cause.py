from lambda_m031d_helpers import ambiguous_m031_report

from decodilo.lambda_cloud.launch_response_loss_root_cause import (
    evaluate_lambda_launch_response_loss_root_cause,
)
from decodilo.lambda_cloud.launch_transport_diagnostics import (
    build_lambda_launch_transport_diagnostics,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report


def test_two_response_losses_block_future_launch():
    report = evaluate_lambda_launch_response_loss_root_cause(
        attempts=[ambiguous_m031_report(), ambiguous_m031_report()]
    )

    assert report.repeated_response_loss_detected is True
    assert report.future_launch_blocked is True
    assert report.root_cause_status == "unknown"


def test_one_response_loss_only_warns():
    success = LambdaM029Report(
        run_id="success",
        real_lambda_api_used=True,
        launch_request_sent=True,
        launch_response_received=True,
        owned_instance_id_redacted="real...1234",
        termination_request_sent=True,
        termination_response_received=True,
        termination_verified=True,
        manual_review_required=False,
        mutating_operations=2,
        billable_action_performed=True,
        estimated_spend=0.01,
        elapsed_seconds=1,
    )
    report = evaluate_lambda_launch_response_loss_root_cause(
        attempts=[ambiguous_m031_report(), success]
    )

    assert report.repeated_response_loss_detected is False
    assert "single launch response loss observed" in report.warnings


def test_transport_timeout_creates_suspected_category():
    report = evaluate_lambda_launch_response_loss_root_cause(
        attempts=[ambiguous_m031_report(), ambiguous_m031_report()],
        transport_diagnostics=build_lambda_launch_transport_diagnostics(
            exception_type="TimeoutError"
        ),
    )

    assert "client_timeout_too_short" in report.likely_categories
    assert report.root_cause_status == "suspected"
