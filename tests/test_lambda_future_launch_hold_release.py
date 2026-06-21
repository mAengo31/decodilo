from lambda_m031d_helpers import closed_m031_incident

from decodilo.lambda_cloud.future_launch_hold_release import (
    evaluate_lambda_future_launch_hold_release,
)
from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import verify_lambda_endpoint_specs
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    accept_lambda_response_loss_mitigation,
)
from decodilo.lambda_cloud.response_loss_regression_harness import (
    run_lambda_response_loss_regression_harness,
)


def _accepted_mitigation():
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
    return accept_lambda_response_loss_mitigation(
        endpoint_verification=endpoint,
        regression_report=run_lambda_response_loss_regression_harness(),
    )


def test_hold_releases_for_future_review_only_when_closed_and_mitigated():
    report = evaluate_lambda_future_launch_hold_release(
        m031_incident_report=closed_m031_incident(),
        mitigation_acceptance=_accepted_mitigation(),
    )

    assert report.hold_released_for_future_review is True
    assert report.future_launch_hold_active is False
    assert report.launch_authorized is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_unaccepted_mitigation_keeps_hold_active():
    accepted = _accepted_mitigation()
    bad = accepted.model_copy(
        update={
            "mitigation_accepted": False,
            "future_launch_hold_can_release": False,
            "blockers": ["endpoint_spec_not_verified"],
        }
    )
    report = evaluate_lambda_future_launch_hold_release(
        m031_incident_report=closed_m031_incident(),
        mitigation_acceptance=bad,
    )

    assert report.future_launch_hold_active is True
    assert "response_loss_mitigation_not_accepted" in report.hold_reasons
