import pytest

from decodilo.lambda_cloud.final_operator_confirmation import (
    LambdaFinalOperatorConfirmation,
    build_lambda_final_operator_confirmation_template,
    evaluate_lambda_final_operator_confirmation,
)


def test_complete_operator_confirmation_passes():
    confirmation = build_lambda_final_operator_confirmation_template(acknowledge_all=True)
    report = evaluate_lambda_final_operator_confirmation(confirmation)

    assert report.confirmation_passed is True
    assert confirmation.launch_allowed is False


def test_missing_ack_blocks():
    report = evaluate_lambda_final_operator_confirmation(LambdaFinalOperatorConfirmation())

    assert report.confirmation_passed is False
    assert report.missing_acknowledgements


def test_over_limit_values_rejected():
    with pytest.raises(ValueError):
        LambdaFinalOperatorConfirmation(requested_max_budget=51)

