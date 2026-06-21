from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import verify_lambda_endpoint_specs
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    accept_lambda_response_loss_mitigation,
)
from decodilo.lambda_cloud.response_loss_regression_harness import (
    run_lambda_response_loss_regression_harness,
)


def _passed_endpoint_report():
    return verify_lambda_endpoint_specs(
        [
            build_lambda_endpoint_spec(
                operation="launch_one_instance",
                method="POST",
                path_template="/instance-operations/launch",
                confidence="medium",
            )
        ]
    )


def test_complete_mitigation_is_accepted():
    report = accept_lambda_response_loss_mitigation(
        endpoint_verification=_passed_endpoint_report(),
        regression_report=run_lambda_response_loss_regression_harness(),
    )

    assert report.mitigation_accepted is True
    assert report.future_launch_hold_can_release is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_endpoint_spec_or_auto_retry_blocks():
    bad_endpoint = verify_lambda_endpoint_specs(
        [
            build_lambda_endpoint_spec(
                operation="launch_one_instance",
                method="GET",
                path_template="/instance-operations/launch",
                confidence="low",
            )
        ]
    )
    report = accept_lambda_response_loss_mitigation(
        endpoint_verification=bad_endpoint,
        regression_report=run_lambda_response_loss_regression_harness(),
        no_automatic_launch_retry_enforced=False,
    )

    assert report.mitigation_accepted is False
    assert "endpoint_spec_not_verified" in report.blockers
    assert "automatic_launch_retry_allowed" in report.blockers
