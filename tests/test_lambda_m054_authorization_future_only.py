from __future__ import annotations

import pytest
from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    LambdaM054SSHConnectivityAuthorization,
    build_lambda_m054_ssh_connectivity_authorization_from_path,
)


def test_m054_authorization_approved_path_is_future_only(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m054_ssh_connectivity_authorization_from_path(paths["risk"])

    assert report.authorization_status == "authorized_for_future_m054_ssh_connectivity_review"
    assert report.future_review_authorized is True
    assert report.ssh_authorized_now is False
    assert report.launch_authorized_now is False
    assert report.remote_command_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m054_authorization_declined_path_stays_not_authorized(tmp_path):
    paths = write_m053_inputs(tmp_path, decline=True)

    report = build_lambda_m054_ssh_connectivity_authorization_from_path(paths["risk"])

    assert report.authorization_status == "not_authorized"
    assert "operator_approval_declined" in report.blockers
    assert report.future_review_authorized is False


def test_m054_authorization_rejects_immediate_execution_flags():
    with pytest.raises(ValueError, match="cannot execute now"):
        LambdaM054SSHConnectivityAuthorization(
            authorization_status="authorized_for_future_m054_ssh_connectivity_review",
            launch_authorized_now=True,
        )
