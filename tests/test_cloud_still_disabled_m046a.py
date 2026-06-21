from __future__ import annotations

from lambda_m046a_helpers import write_m046a_inputs

from decodilo.lambda_cloud.capacity_selected_execution_gate_check import (
    load_lambda_capacity_selected_execution_gate_check,
)
from decodilo.lambda_cloud.m046a_report import load_lambda_m046a_report


def test_cloud_still_disabled_m046a(tmp_path):
    paths = write_m046a_inputs(tmp_path)
    gate = load_lambda_capacity_selected_execution_gate_check(
        paths["execution_gate_m046"]
    )
    report = load_lambda_m046a_report(paths["m046a"])

    assert gate.launch_ready is False
    assert gate.launch_allowed is False
    assert gate.billable_action_performed is False
    assert gate.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
