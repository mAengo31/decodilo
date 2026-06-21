import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.ssh_operator_approval import (
    LambdaSSHOperatorApprovalReport,
    build_lambda_ssh_operator_approval,
)


def test_ssh_operator_approval_decline_and_connectivity_only():
    declined = build_lambda_ssh_operator_approval(decline_ssh=True)
    assert declined.approval_status == "declined_no_ssh"
    assert declined.ssh_connectivity_allowed is False

    approved = build_lambda_ssh_operator_approval(
        approve_connectivity_only=True,
        acknowledge_all=True,
    )
    assert approved.approval_status == "approved_ssh_connectivity_check_only"
    assert approved.ssh_connectivity_allowed is True
    assert approved.single_allowlisted_command_allowed is False
    assert approved.launch_ready is False
    assert approved.launch_allowed is False


def test_ssh_operator_approval_rejects_interactive_shell_status():
    with pytest.raises(ValidationError):
        LambdaSSHOperatorApprovalReport(
            approval_status="approved_interactive_shell",
            approval_complete=True,
        )
