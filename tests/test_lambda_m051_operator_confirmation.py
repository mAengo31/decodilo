from __future__ import annotations

import pytest

from decodilo.lambda_cloud.m051_operator_confirmation import (
    LambdaM051OperatorConfirmation,
    build_lambda_m051_operator_confirmation,
)


def test_m051_operator_confirmation_complete():
    report = build_lambda_m051_operator_confirmation(
        confirm_metadata_only_bootstrap=True,
        acknowledge_all=True,
    )

    assert report.confirmation_status == "confirmed_for_m051_one_shot_metadata_bootstrap"
    assert report.confirmation_hash
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False


def test_m051_operator_confirmation_incomplete_blocks():
    report = build_lambda_m051_operator_confirmation(
        confirm_metadata_only_bootstrap=True,
        acknowledge_all=False,
    )

    assert report.confirmation_status == "not_provided"
    assert "billable_instance_acknowledged" in report.blockers


def test_m051_operator_confirmation_rejects_forbidden_status():
    with pytest.raises(ValueError):
        LambdaM051OperatorConfirmation.model_validate(
            {
                "confirmation_status": "launch_now",
                "launch_ready": False,
                "launch_allowed": False,
            }
        )
