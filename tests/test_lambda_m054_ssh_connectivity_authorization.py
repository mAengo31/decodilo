from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    build_lambda_m054_ssh_connectivity_authorization_from_path,
)


def test_m054_authorization_not_authorized_without_operator_approval(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=False)

    report = build_lambda_m054_ssh_connectivity_authorization_from_path(paths["risk"])

    assert report.authorization_status == "not_authorized"
    assert "operator_approval_not_provided" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.ssh_authorized_now is False


def test_m054_authorization_future_only_when_approval_complete(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m054_ssh_connectivity_authorization_from_path(paths["risk"])

    assert report.authorization_status == "authorized_for_future_m054_ssh_connectivity_review"
    assert report.future_review_authorized is True
    assert report.launch_authorized_now is False
    assert report.ssh_authorized_now is False
    assert report.remote_command_authorized_now is False
