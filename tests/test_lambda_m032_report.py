from lambda_m031d_helpers import closed_m031_incident

from decodilo.lambda_cloud.future_launch_hold_release import (
    evaluate_lambda_future_launch_hold_release,
)
from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import verify_lambda_endpoint_specs
from decodilo.lambda_cloud.m032_report import build_lambda_m032_report
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    accept_lambda_response_loss_mitigation,
)
from decodilo.lambda_cloud.response_loss_regression_harness import (
    run_lambda_response_loss_regression_harness,
)


def test_m032_report_builds_with_hold_release_for_review():
    endpoint = verify_lambda_endpoint_specs(
        [
            build_lambda_endpoint_spec(
                operation="launch_one_instance",
                method="POST",
                path_template="/instance-operations/launch",
                confidence="medium",
            )
        ]
    )
    regression = run_lambda_response_loss_regression_harness()
    acceptance = accept_lambda_response_loss_mitigation(
        endpoint_verification=endpoint,
        regression_report=regression,
    )
    hold = evaluate_lambda_future_launch_hold_release(
        m031_incident_report=closed_m031_incident(),
        mitigation_acceptance=acceptance,
    )

    report = build_lambda_m032_report(
        endpoint_verification=endpoint,
        regression_report=regression,
        mitigation_acceptance=acceptance,
        hold_release=hold,
    )

    assert report.response_capture_implemented is True
    assert report.diagnostics_implemented is True
    assert report.regression_harness_passed is True
    assert report.mitigation_accepted is True
    assert report.future_launch_hold_released_for_review is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
