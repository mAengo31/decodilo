from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.no_training_policy import (
    LambdaNoTrainingPolicyReport,
    write_lambda_no_training_policy,
)
from decodilo.lambda_cloud.ssh_connectivity_risk_review import (
    build_lambda_ssh_connectivity_risk_review_from_paths,
)


def test_ssh_connectivity_risk_review_is_planning_incomplete_without_approval(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=False)

    report = build_lambda_ssh_connectivity_risk_review_from_paths(
        scope=paths["scope"],
        credential_policy=paths["credential"],
        client_policy=paths["client"],
        evidence_schema=paths["evidence_schema"],
        operator_approval=paths["operator"],
        remote_command_prohibition=paths["remote_prohibition"],
        file_transfer_prohibition=paths["file_prohibition"],
        port_forwarding_prohibition=paths["port_prohibition"],
        package_install_policy=paths["package"],
        no_training_policy=paths["training"],
        m052_report=paths["m052"],
    )

    assert report.risk_review_status == "planning_incomplete"
    assert report.risk_review_passed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_risk_review_passes_with_approval_and_prohibitions(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_ssh_connectivity_risk_review_from_paths(
        scope=paths["scope"],
        credential_policy=paths["credential"],
        client_policy=paths["client"],
        evidence_schema=paths["evidence_schema"],
        operator_approval=paths["operator"],
        remote_command_prohibition=paths["remote_prohibition"],
        file_transfer_prohibition=paths["file_prohibition"],
        port_forwarding_prohibition=paths["port_prohibition"],
        package_install_policy=paths["package"],
        no_training_policy=paths["training"],
        m052_report=paths["m052"],
    )

    assert report.risk_review_status == "passed"
    assert report.risk_review_passed is True


def test_ssh_connectivity_risk_review_blocks_if_training_allowed(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)
    write_lambda_no_training_policy(
        paths["training"],
        LambdaNoTrainingPolicyReport.model_construct(training_allowed=True),
    )

    report = build_lambda_ssh_connectivity_risk_review_from_paths(
        scope=paths["scope"],
        credential_policy=paths["credential"],
        client_policy=paths["client"],
        evidence_schema=paths["evidence_schema"],
        operator_approval=paths["operator"],
        remote_command_prohibition=paths["remote_prohibition"],
        file_transfer_prohibition=paths["file_prohibition"],
        port_forwarding_prohibition=paths["port_prohibition"],
        package_install_policy=paths["package"],
        no_training_policy=paths["training"],
        m052_report=paths["m052"],
    )

    assert report.risk_review_status == "blocked"
    assert "training_not_denied" in report.blockers
