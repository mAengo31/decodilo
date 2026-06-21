from lambda_m033_helpers import endpoint_verification

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    build_lambda_endpoint_spec_operator_confirmation,
)


def test_no_confirmation_blocks_endpoint_acceptance():
    report = build_lambda_endpoint_spec_operator_confirmation(
        endpoint_verification=endpoint_verification()
    )

    assert report.confirmation_passed is False
    assert "operator_launch_endpoint_confirmation_missing" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_medium_confidence_requires_explicit_acceptance():
    report = build_lambda_endpoint_spec_operator_confirmation(
        endpoint_verification=endpoint_verification("medium"),
        operator_confirms_launch_endpoint=True,
        operator_confirms_terminate_endpoint=True,
    )

    assert report.confirmation_passed is False
    assert "operator_medium_confidence_acceptance_missing" in report.blockers


def test_medium_confidence_with_acceptance_passes_for_future_review():
    report = build_lambda_endpoint_spec_operator_confirmation(
        endpoint_verification=endpoint_verification("medium"),
        operator_confirms_launch_endpoint=True,
        operator_confirms_terminate_endpoint=True,
        operator_accepts_medium_confidence=True,
    )

    assert report.confirmation_passed is True
    assert report.confirmation.confirmation_status == "confirmed_medium_confidence_accepted"
    assert report.launch_allowed is False


def test_high_confidence_passes_without_medium_acceptance():
    report = build_lambda_endpoint_spec_operator_confirmation(
        endpoint_verification=endpoint_verification("high"),
        operator_confirms_launch_endpoint=True,
        operator_confirms_terminate_endpoint=True,
    )

    assert report.confirmation_passed is True
    assert report.confirmation.confirmation_status == "confirmed_high_confidence"
