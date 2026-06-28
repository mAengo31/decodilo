from __future__ import annotations

from lambda_m058_helpers import write_m057_noop_workdir

from decodilo.lambda_cloud.ssh_noop_command_closeout import (
    build_lambda_ssh_noop_command_closeout_from_paths,
)
from decodilo.lambda_cloud.ssh_noop_command_evidence_package import (
    build_lambda_ssh_noop_command_evidence_package_from_paths,
    write_lambda_ssh_noop_command_evidence_package,
)
from decodilo.lambda_cloud.ssh_noop_command_reconciliation import (
    build_lambda_ssh_noop_command_reconciliation_from_paths,
    write_lambda_ssh_noop_command_reconciliation,
)
from decodilo.lambda_cloud.ssh_noop_command_success_record import (
    build_lambda_ssh_noop_command_success_record_from_paths,
    write_lambda_ssh_noop_command_success_record,
)


def _closeout_inputs(tmp_path, **kwargs):
    paths = write_m057_noop_workdir(tmp_path, **kwargs)
    success = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )
    success_path = tmp_path / "success.json"
    write_lambda_ssh_noop_command_success_record(success_path, success)
    reconcile = build_lambda_ssh_noop_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        final_discovery=paths["post_discovery"],
    )
    reconcile_path = tmp_path / "reconcile.json"
    write_lambda_ssh_noop_command_reconciliation(reconcile_path, reconcile)
    evidence = build_lambda_ssh_noop_command_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconcile_path,
        secret_scan=paths["secret_scan"],
    )
    evidence_path = tmp_path / "evidence.json"
    write_lambda_ssh_noop_command_evidence_package(evidence_path, evidence)
    return success_path, reconcile_path, evidence_path


def test_noop_closeout_succeeds_for_clean_fixture(tmp_path):
    success, reconcile, evidence = _closeout_inputs(tmp_path)

    closeout = build_lambda_ssh_noop_command_closeout_from_paths(
        success_record=success,
        reconciliation=reconcile,
        evidence_package=evidence,
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.command_scope_respected is True
    assert closeout.billable_action_performed is False
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False


def test_noop_closeout_blocks_unverified_termination(tmp_path):
    success, reconcile, evidence = _closeout_inputs(
        tmp_path,
        termination_verified=False,
    )

    closeout = build_lambda_ssh_noop_command_closeout_from_paths(
        success_record=success,
        reconciliation=reconcile,
        evidence_package=evidence,
    )

    assert closeout.closeout_succeeded is False
    assert "termination_not_verified" in closeout.blockers
