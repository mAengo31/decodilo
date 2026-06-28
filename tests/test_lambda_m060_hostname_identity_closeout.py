from __future__ import annotations

import pytest
from lambda_m060_helpers import write_m059_hostname_workdir

from decodilo.lambda_cloud.m060_report import build_lambda_m060_report_from_paths
from decodilo.lambda_cloud.m061_next_step_decision import (
    LambdaM061NextStepDecision,
    build_lambda_m061_next_step_decision_from_paths,
    write_lambda_m061_next_step_decision,
)
from decodilo.lambda_cloud.m061_whoami_authorization import (
    LambdaM061WhoamiAuthorization,
    build_lambda_m061_whoami_authorization_from_paths,
    write_lambda_m061_whoami_authorization,
)
from decodilo.lambda_cloud.ssh_hostname_identity_closeout import (
    build_lambda_ssh_hostname_identity_closeout_from_paths,
    write_lambda_ssh_hostname_identity_closeout,
)
from decodilo.lambda_cloud.ssh_hostname_identity_evidence_package import (
    build_lambda_ssh_hostname_identity_evidence_package_from_paths,
    write_lambda_ssh_hostname_identity_evidence_package,
)
from decodilo.lambda_cloud.ssh_hostname_identity_reconciliation import (
    build_lambda_ssh_hostname_identity_reconciliation_from_paths,
    write_lambda_ssh_hostname_identity_reconciliation,
)
from decodilo.lambda_cloud.ssh_hostname_identity_success_record import (
    build_lambda_ssh_hostname_identity_success_record_from_paths,
    write_lambda_ssh_hostname_identity_success_record,
)


def _write_m060_chain(tmp_path, **kwargs):
    paths = write_m059_hostname_workdir(tmp_path, **kwargs)
    success_path = tmp_path / "success.json"
    success = build_lambda_ssh_hostname_identity_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )
    write_lambda_ssh_hostname_identity_success_record(success_path, success)
    reconciliation_path = tmp_path / "reconciliation.json"
    reconciliation = build_lambda_ssh_hostname_identity_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        final_discovery=paths["post_discovery"],
    )
    write_lambda_ssh_hostname_identity_reconciliation(
        reconciliation_path,
        reconciliation,
    )
    evidence_path = tmp_path / "evidence.json"
    evidence = build_lambda_ssh_hostname_identity_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
    )
    write_lambda_ssh_hostname_identity_evidence_package(evidence_path, evidence)
    closeout_path = tmp_path / "closeout.json"
    closeout = build_lambda_ssh_hostname_identity_closeout_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
    )
    write_lambda_ssh_hostname_identity_closeout(closeout_path, closeout)
    decision_path = tmp_path / "decision.json"
    decision = build_lambda_m061_next_step_decision_from_paths(
        hostname_closeout=closeout_path,
    )
    write_lambda_m061_next_step_decision(decision_path, decision)
    report_path = tmp_path / "m060.json"
    report = build_lambda_m060_report_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
        closeout=closeout_path,
        decision=decision_path,
    )
    report_path.write_text(report.to_json(), encoding="utf-8")
    authorization_path = tmp_path / "m061-authorization.json"
    authorization = build_lambda_m061_whoami_authorization_from_paths(
        m060_report=report_path,
        hostname_closeout=closeout_path,
        decision=decision_path,
    )
    write_lambda_m061_whoami_authorization(authorization_path, authorization)
    return {
        **paths,
        "success": success_path,
        "reconciliation": reconciliation_path,
        "evidence": evidence_path,
        "closeout": closeout_path,
        "decision": decision_path,
        "m060_report": report_path,
        "authorization": authorization_path,
    }


def test_hostname_success_record_passes_clean_m059_fixture(tmp_path):
    paths = write_m059_hostname_workdir(tmp_path)

    record = build_lambda_ssh_hostname_identity_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status == "ssh_hostname_identity_success"
    assert record.command == "hostname"
    assert record.stdout_captured_redacted is True
    assert record.stdout_stored is False
    assert record.termination_verified is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_hostname_success_record_blocks_raw_stdout(tmp_path):
    paths = write_m059_hostname_workdir(
        tmp_path,
        stdout_stored=True,
        stdout_redacted="fixture-hostname",
    )

    record = build_lambda_ssh_hostname_identity_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status != "ssh_hostname_identity_success"
    assert "hostname_stdout_not_redacted" in record.blockers
    assert "stdout_stored" in record.blockers


def test_hostname_reconciliation_blocks_visible_instance(tmp_path):
    paths = _write_m060_chain(tmp_path, final_instance_count=1)

    reconciliation = build_lambda_ssh_hostname_identity_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=paths["success"],
        final_discovery=paths["post_discovery"],
    )

    assert reconciliation.reconciliation_passed is False
    assert "final_discovery_visible_instances_present" in reconciliation.errors


def test_m060_chain_closes_and_points_to_future_whoami_review(tmp_path):
    paths = _write_m060_chain(tmp_path)

    closeout = build_lambda_ssh_hostname_identity_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )
    decision = build_lambda_m061_next_step_decision_from_paths(
        hostname_closeout=paths["closeout"],
    )
    authorization = build_lambda_m061_whoami_authorization_from_paths(
        m060_report=paths["m060_report"],
        hostname_closeout=paths["closeout"],
        decision=paths["decision"],
    )
    report = build_lambda_m060_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
        closeout=paths["closeout"],
        decision=paths["decision"],
        authorization=paths["authorization"],
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status == "closed_with_warnings"
    assert decision.decision_status == "plan_whoami_identity_command_review"
    assert decision.next_allowed_review_command == "whoami"
    assert decision.command_authorized_now is False
    assert (
        authorization.authorization_status
        == "authorized_for_future_m061_whoami_identity_command_review"
    )
    assert authorization.selected_future_command_set == ["whoami"]
    assert authorization.command_authorized_now is False
    assert report.report_passed is True
    assert report.m061_decision == "plan_whoami_identity_command_review"
    assert (
        report.m061_authorization_status
        == "authorized_for_future_m061_whoami_identity_command_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False


def test_m061_authorization_blocks_failed_hostname_closeout(tmp_path):
    paths = _write_m060_chain(tmp_path, stdout_stored=True, stdout_redacted="raw-host")

    authorization = build_lambda_m061_whoami_authorization_from_paths(
        m060_report=paths["m060_report"],
        hostname_closeout=paths["closeout"],
        decision=paths["decision"],
    )

    assert authorization.authorization_status == "not_authorized"
    assert "m060_report_not_passed" in authorization.blockers
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_forbidden_m061_immediate_status_is_rejected():
    with pytest.raises(ValueError):
        LambdaM061NextStepDecision(decision_status="launch_now")  # type: ignore[arg-type]


def test_m061_authorization_rejects_immediate_execution_flags():
    with pytest.raises(ValueError):
        LambdaM061WhoamiAuthorization(
            authorization_status="authorized_for_future_m061_whoami_identity_command_review",
            selected_future_command_set=["whoami"],
            command_authorized_now=True,
        )
