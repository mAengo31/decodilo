import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    LambdaCapacitySelectedOperatorApproval,
    build_lambda_capacity_selected_operator_approval,
)


def test_capacity_selected_operator_approval_complete_future_only():
    report = build_lambda_capacity_selected_operator_approval(
        approve_future_m046=True,
        acknowledge_all=True,
    )

    assert (
        report.approval_status
        == "approved_for_future_m046_capacity_selected_launch_review"
    )
    assert report.approval_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_selected_operator_approval_missing_ack_blocks():
    report = build_lambda_capacity_selected_operator_approval(
        approve_future_m046=True,
        acknowledge_all=False,
    )

    assert report.approval_status == "not_provided"
    assert any(blocker.startswith("missing_acknowledgement:") for blocker in report.blockers)


def test_capacity_selected_operator_approval_decline_wait():
    report = build_lambda_capacity_selected_operator_approval(decline_wait=True)

    assert report.approval_status == "declined_wait_for_live_availability"
    assert report.approval_complete is True


def test_capacity_selected_operator_approval_decline_manual():
    report = build_lambda_capacity_selected_operator_approval(
        decline_manual_selection=True
    )

    assert report.approval_status == "declined_manual_candidate_selection"
    assert report.approval_complete is True


def test_capacity_selected_operator_approval_forbidden_status_rejected():
    with pytest.raises(ValidationError):
        LambdaCapacitySelectedOperatorApproval.model_validate(
            {
                "approval_status": "launch_now",
                "approval_complete": False,
            }
        )
