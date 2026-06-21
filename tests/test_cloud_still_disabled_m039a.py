from __future__ import annotations

from lambda_m038_helpers import execution_gate_check, m038a_report


def test_m039a_artifacts_keep_cloud_execution_disabled():
    gate = execution_gate_check(approval_complete=True)
    report = m038a_report(approval_complete=True)

    assert gate.launch_ready is False
    assert gate.launch_allowed is False
    assert gate.billable_action_performed is False
    assert gate.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
