from __future__ import annotations

from lambda_m037r_helpers import ssh_selection
from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
    write_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.capacity_selected_execution_gate_check import (
    build_lambda_capacity_selected_execution_gate_check_from_paths,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    build_lambda_capacity_selected_operator_approval,
    write_lambda_capacity_selected_operator_approval,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)


def _gate(paths):
    return build_lambda_capacity_selected_execution_gate_check_from_paths(
        m046_authorization=paths["authorization_m046"],
        cost_risk_review=paths["cost_m045"],
        operator_approval=paths["approval_m045"],
        capacity_selected_gate_check=paths["gate_m045"],
        capacity_aware_selector_output=paths["selector_m044h"],
        capacity_aware_selector_authorization=paths["authorization_m044h"],
        capacity_aware_selector_gate_check=paths["gate_m044h"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )


def test_capacity_selected_execution_gate_valid_artifacts_pass(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = _gate(paths)

    assert report.gate_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.raw_ssh_key_available_for_request_construction is True
    assert report.old_path_fallback_blocked is True
    assert report.m039_path_fallback_blocked is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_selected_execution_gate_missing_authorization_blocks(tmp_path):
    paths = write_m045_inputs(tmp_path, approve=False)
    report = _gate(paths)

    assert report.gate_passed is False
    assert "m046_capacity_selected_authorization_not_ready" in report.blockers


def test_capacity_selected_execution_gate_wrong_candidate_blocks(tmp_path):
    paths = write_m045_inputs(tmp_path)
    selector = load_lambda_capacity_history_aware_selector(paths["selector_m044h"])
    assert selector.selected_candidate is not None
    wrong_selector = selector.model_copy(
        update={
            "selected_candidate": selector.selected_candidate.model_copy(
                update={"shape": "gpu_1x_h100_pcie"}
            )
        }
    )
    write_lambda_capacity_history_aware_selector(
        paths["selector_m044h"],
        wrong_selector,
    )

    report = _gate(paths)

    assert report.gate_passed is False
    assert "capacity_aware_selector_candidate_mismatch" in report.blockers


def test_capacity_selected_execution_gate_missing_raw_ssh_blocks(tmp_path):
    paths = write_m045_inputs(tmp_path)
    write_lambda_existing_ssh_key_selection(
        paths["ssh"],
        ssh_selection().model_copy(update={"selected_ssh_key_name_for_payload": None}),
    )

    report = _gate(paths)

    assert report.gate_passed is False
    assert "raw_existing_ssh_key_name_missing_from_private_artifact" in report.blockers


def test_capacity_selected_execution_gate_incomplete_approval_blocks(tmp_path):
    paths = write_m045_inputs(tmp_path)
    approval = build_lambda_capacity_selected_operator_approval()
    write_lambda_capacity_selected_operator_approval(paths["approval_m045"], approval)

    report = _gate(paths)

    assert report.gate_passed is False
    assert "capacity_selected_operator_approval_not_approved" in report.blockers
