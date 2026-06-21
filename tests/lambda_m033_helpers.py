from lambda_m029d_helpers import ambiguous_m029_report
from lambda_m030_helpers import m029_authorization_package
from lambda_m031d_helpers import closed_m031_closeout, closed_m031_incident

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    build_lambda_endpoint_spec_operator_confirmation,
)
from decodilo.lambda_cloud.future_launch_hold_release import (
    evaluate_lambda_future_launch_hold_release,
)
from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import verify_lambda_endpoint_specs
from decodilo.lambda_cloud.launch_timeout_policy import build_lambda_launch_timeout_policy
from decodilo.lambda_cloud.response_capture_settings_lock import (
    build_lambda_response_capture_settings_lock,
)
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    accept_lambda_response_loss_mitigation,
)
from decodilo.lambda_cloud.response_loss_regression_harness import (
    run_lambda_response_loss_regression_harness,
)
from decodilo.lambda_cloud.third_attempt_authorization import (
    build_lambda_third_attempt_authorization,
)
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    build_lambda_third_attempt_correlation_plan,
)
from decodilo.lambda_cloud.third_attempt_go_no_go import (
    build_lambda_third_attempt_go_no_go,
)
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    build_lambda_third_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.third_attempt_risk_review import (
    build_lambda_third_attempt_risk_review,
)


def endpoint_verification(confidence: str = "medium"):
    return verify_lambda_endpoint_specs(
        [
            build_lambda_endpoint_spec(
                operation="launch_one_instance",
                method="POST",
                path_template="/instance-operations/launch",
                source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
                confidence=confidence,
            ),
            build_lambda_endpoint_spec(
                operation="terminate_owned_instance",
                method="POST",
                path_template="/instance-operations/terminate",
                source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
                confidence=confidence,
            ),
        ]
    )


def mitigation_acceptance():
    return accept_lambda_response_loss_mitigation(
        endpoint_verification=endpoint_verification(),
        regression_report=run_lambda_response_loss_regression_harness(),
    )


def endpoint_confirmation(*, accept_medium: bool = True, confidence: str = "medium"):
    return build_lambda_endpoint_spec_operator_confirmation(
        endpoint_verification=endpoint_verification(confidence),
        operator_confirms_launch_endpoint=True,
        operator_confirms_terminate_endpoint=True,
        operator_accepts_medium_confidence=accept_medium,
    )


def capture_lock():
    return build_lambda_response_capture_settings_lock()


def timeout_policy():
    return build_lambda_launch_timeout_policy()


def hold_release():
    return evaluate_lambda_future_launch_hold_release(
        m031_incident_report=closed_m031_incident(),
        mitigation_acceptance=mitigation_acceptance(),
    )


def risk_review():
    return build_lambda_third_attempt_risk_review(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m031d_closeout=closed_m031_closeout(),
        mitigation_acceptance=mitigation_acceptance(),
        endpoint_confirmation=endpoint_confirmation(),
        timeout_policy=timeout_policy(),
    )


def correlation_plan():
    return build_lambda_third_attempt_correlation_plan(
        m029_authorization=m029_authorization_package(),
        response_capture_lock=capture_lock(),
        timeout_policy=timeout_policy(),
    )


def reconciliation_plan():
    return build_lambda_third_attempt_reconciliation_plan()


def third_attempt_authorization(**overrides):
    defaults = {
        "m031_closeout": closed_m031_closeout(),
        "mitigation_acceptance": mitigation_acceptance(),
        "hold_release": hold_release(),
        "endpoint_confirmation": endpoint_confirmation(),
        "response_capture_lock": capture_lock(),
        "timeout_policy": timeout_policy(),
        "risk_review": risk_review(),
        "correlation_plan": correlation_plan(),
        "reconciliation_plan": reconciliation_plan(),
        "fresh_readonly_discovery_present": True,
        "budget_resource_checks_valid": True,
        "renewed_operator_approval_present": True,
    }
    defaults.update(overrides)
    return build_lambda_third_attempt_authorization(**defaults)


def third_attempt_go_no_go():
    return build_lambda_third_attempt_go_no_go(third_attempt_authorization())
