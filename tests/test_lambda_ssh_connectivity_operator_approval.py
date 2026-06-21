from __future__ import annotations

import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.ssh_connectivity_operator_approval import (
    LambdaSSHConnectivityOperatorApprovalReport,
    build_lambda_ssh_connectivity_operator_approval,
)


def test_ssh_connectivity_operator_approval_complete_future_only():
    report = build_lambda_ssh_connectivity_operator_approval(
        approve_future_m054=True,
        acknowledge_all=True,
    )

    assert report.approval_status == "approved_for_future_m054_ssh_connectivity_review"
    assert report.approval_complete is True
    assert report.ssh_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_operator_approval_missing_ack_blocks():
    report = build_lambda_ssh_connectivity_operator_approval(
        approve_future_m054=True,
        acknowledge_all=False,
    )

    assert report.approval_status == "not_provided"
    assert "missing_required_ssh_connectivity_acknowledgements" in report.blockers


def test_ssh_connectivity_operator_decline_works():
    report = build_lambda_ssh_connectivity_operator_approval(decline=True)

    assert report.approval_status == "declined"
    assert report.approval_complete is True


def test_ssh_connectivity_operator_forbidden_flags_rejected():
    with pytest.raises(ValidationError):
        LambdaSSHConnectivityOperatorApprovalReport(
            approval_status="not_provided",
            ssh_authorized_now=True,
        )
