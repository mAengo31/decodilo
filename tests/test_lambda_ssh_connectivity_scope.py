from __future__ import annotations

import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.ssh_connectivity_scope import (
    LambdaSSHConnectivityScopeReport,
    build_lambda_ssh_connectivity_scope,
)


def test_ssh_connectivity_scope_allows_handshake_only_and_forbids_exec_surfaces():
    report = build_lambda_ssh_connectivity_scope()

    assert "ssh_connectivity_handshake_only" in report.allowed_future_modes
    assert "remote_exec" in report.forbidden_actions
    assert "file_transfer" in report.forbidden_actions
    assert "port_forwarding" in report.forbidden_actions
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_scope_rejects_missing_remote_exec_forbidden_action():
    with pytest.raises(ValidationError):
        LambdaSSHConnectivityScopeReport(
            forbidden_actions=["interactive_shell"],
        )
