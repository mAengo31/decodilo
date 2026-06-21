from lambda_m036_helpers import support_response

from decodilo.lambda_cloud.support_confirmation_validator import (
    validate_lambda_support_confirmation_response,
)


def test_complete_support_confirmation_response_produces_high_candidate():
    report = validate_lambda_support_confirmation_response(support_response())

    assert report.validation_passed is True
    assert report.endpoint_confidence_candidate == "high"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_ambiguous_behavior_blocks_validation():
    report = validate_lambda_support_confirmation_response(
        support_response(missing=("ambiguous_launch_reconciliation",))
    )

    assert report.validation_passed is False
    assert "missing_ambiguous_launch_reconciliation" in report.blockers


def test_missing_terminate_verification_blocks_validation():
    report = validate_lambda_support_confirmation_response(
        support_response(missing=("termination_verification",))
    )

    assert report.validation_passed is False
    assert "missing_termination_verification" in report.blockers

