from __future__ import annotations

from lambda_m060_helpers import write_m059_hostname_workdir

from decodilo.lambda_cloud.m060_report import build_lambda_m060_report_from_paths
from decodilo.lambda_cloud.m061_next_step_decision import (
    build_lambda_m061_next_step_decision_from_paths,
    write_lambda_m061_next_step_decision,
)
from decodilo.lambda_cloud.preflight import run_lambda_preflight
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


def test_m060_keeps_cloud_launch_and_remote_command_disabled(tmp_path):
    paths = write_m059_hostname_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    write_lambda_ssh_hostname_identity_success_record(
        success_path,
        build_lambda_ssh_hostname_identity_success_record_from_paths(
            workdir=paths["workdir"],
            final_discovery=paths["post_discovery"],
        ),
    )
    reconciliation_path = tmp_path / "reconciliation.json"
    write_lambda_ssh_hostname_identity_reconciliation(
        reconciliation_path,
        build_lambda_ssh_hostname_identity_reconciliation_from_paths(
            workdir=paths["workdir"],
            success_record=success_path,
            final_discovery=paths["post_discovery"],
        ),
    )
    evidence_path = tmp_path / "evidence.json"
    write_lambda_ssh_hostname_identity_evidence_package(
        evidence_path,
        build_lambda_ssh_hostname_identity_evidence_package_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
        ),
    )
    closeout_path = tmp_path / "closeout.json"
    write_lambda_ssh_hostname_identity_closeout(
        closeout_path,
        build_lambda_ssh_hostname_identity_closeout_from_paths(
            success_record=success_path,
            reconciliation=reconciliation_path,
            evidence_package=evidence_path,
        ),
    )
    decision_path = tmp_path / "decision.json"
    write_lambda_m061_next_step_decision(
        decision_path,
        build_lambda_m061_next_step_decision_from_paths(
            hostname_closeout=closeout_path,
        ),
    )
    report = build_lambda_m060_report_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
        closeout=closeout_path,
        decision=decision_path,
    )

    preflight = run_lambda_preflight(m060_report=report)

    assert report.report_passed is True
    assert report.billable_action_performed is False
    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
    assert preflight.real_mutation_enabled is False
    assert preflight.m060_hostname_identity_closeout_summary is not None
    assert preflight.m060_hostname_identity_closeout_summary["report_passed"] is True
