from __future__ import annotations

import pytest

from decodilo.lambda_cloud.ssh_connectivity_operator_approval import (
    LambdaSSHConnectivityOperatorApprovalReport,
    build_lambda_ssh_connectivity_operator_approval,
)


def test_ssh_connectivity_operator_approval_accepts_future_review_only():
    report = build_lambda_ssh_connectivity_operator_approval(
        approve_future_m054=True,
        acknowledge_all=True,
    )

    assert report.approval_status == "approved_for_future_m054_ssh_connectivity_review"
    assert report.approval_complete is True
    assert report.ssh_authorized_now is False
    assert report.launch_authorized_now is False
    assert report.remote_exec_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_operator_approval_declines_future_review():
    report = build_lambda_ssh_connectivity_operator_approval(decline=True)

    assert report.approval_status == "declined"
    assert report.approval_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_operator_approval_missing_ack_blocks_acceptance():
    report = build_lambda_ssh_connectivity_operator_approval(
        approve_future_m054=True,
        acknowledge_all=False,
    )

    assert report.approval_status == "not_provided"
    assert report.approval_complete is False
    assert "missing_required_ssh_connectivity_acknowledgements" in report.blockers


def test_ssh_connectivity_operator_approval_rejects_forbidden_now_flags():
    with pytest.raises(ValueError, match="cannot authorize immediate SSH"):
        LambdaSSHConnectivityOperatorApprovalReport(
            approval_status="approved_for_future_m054_ssh_connectivity_review",
            approval_complete=True,
            ssh_authorized_now=True,
        )
