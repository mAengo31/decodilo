from __future__ import annotations

from pathlib import Path

from lambda_m044_helpers import m044_price_snapshot
from lambda_m044h_helpers import write_m044h_inputs

from decodilo.lambda_cloud.capacity_selected_command_preview import (
    build_lambda_capacity_selected_command_preview_from_paths,
    write_lambda_capacity_selected_command_preview,
)
from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    build_lambda_capacity_selected_cost_risk_review_from_paths,
    write_lambda_capacity_selected_cost_risk_review,
)
from decodilo.lambda_cloud.capacity_selected_gate_check import (
    build_lambda_capacity_selected_gate_check_from_paths,
    write_lambda_capacity_selected_gate_check,
)
from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    build_lambda_capacity_selected_m046_authorization_from_paths,
    write_lambda_capacity_selected_m046_authorization,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    build_lambda_capacity_selected_operator_approval,
    write_lambda_capacity_selected_operator_approval,
)
from decodilo.lambda_cloud.m045_decision_record import (
    build_lambda_m045_decision_record_from_paths,
    write_lambda_m045_decision_record,
)
from decodilo.lambda_cloud.m045_report import (
    build_lambda_m045_report_from_paths,
    write_lambda_m045_report,
)


def write_m045_inputs(
    tmp_path: Path,
    *,
    approve: bool = True,
    decline_wait: bool = False,
    decline_manual: bool = False,
    sample_price: bool = False,
    over_budget: bool = False,
) -> dict[str, Path]:
    paths = write_m044h_inputs(
        tmp_path,
        prices=m044_price_snapshot(sample=sample_price, over_budget=over_budget),
    )
    paths.update(
        {
            "cost_m045": tmp_path / "capacity-selected-cost-risk-review.json",
            "approval_m045": tmp_path / "capacity-selected-operator-approval.json",
            "authorization_m046": tmp_path / "m046-authorization.json",
            "gate_m045": tmp_path / "capacity-selected-gate-check.json",
            "preview_m046": tmp_path / "m046-command-preview.json",
            "decision_m045": tmp_path / "m045-decision.json",
            "m045": tmp_path / "m045-report.json",
        }
    )
    cost = build_lambda_capacity_selected_cost_risk_review_from_paths(
        selector_output=paths["selector_m044h"],
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        response_loss_controls=paths["controls"],
        ssh_key_selection=paths["ssh"],
    )
    write_lambda_capacity_selected_cost_risk_review(paths["cost_m045"], cost)
    approval = build_lambda_capacity_selected_operator_approval(
        approve_future_m046=approve,
        decline_wait=decline_wait,
        decline_manual_selection=decline_manual,
        acknowledge_all=approve,
    )
    write_lambda_capacity_selected_operator_approval(paths["approval_m045"], approval)
    authorization = build_lambda_capacity_selected_m046_authorization_from_paths(
        cost_risk_review=paths["cost_m045"],
        operator_approval=paths["approval_m045"],
        selector_authorization=paths["authorization_m044h"],
        selector_gate_check=paths["gate_m044h"],
        response_loss_controls=paths["controls"],
        ssh_key_selection=paths["ssh"],
    )
    write_lambda_capacity_selected_m046_authorization(
        paths["authorization_m046"],
        authorization,
    )
    gate = build_lambda_capacity_selected_gate_check_from_paths(
        authorization=paths["authorization_m046"],
        cost_risk_review=paths["cost_m045"],
        operator_approval=paths["approval_m045"],
        response_loss_controls=paths["controls"],
    )
    write_lambda_capacity_selected_gate_check(paths["gate_m045"], gate)
    preview = build_lambda_capacity_selected_command_preview_from_paths(
        authorization=paths["authorization_m046"],
        gate_check=paths["gate_m045"],
    )
    write_lambda_capacity_selected_command_preview(paths["preview_m046"], preview)
    decision = build_lambda_m045_decision_record_from_paths(
        operator_approval=paths["approval_m045"],
        authorization=paths["authorization_m046"],
    )
    write_lambda_m045_decision_record(paths["decision_m045"], decision)
    report = build_lambda_m045_report_from_paths(
        cost_risk_review=paths["cost_m045"],
        operator_approval=paths["approval_m045"],
        decision=paths["decision_m045"],
        authorization=paths["authorization_m046"],
        gate_check=paths["gate_m045"],
        command_preview=paths["preview_m046"],
    )
    write_lambda_m045_report(paths["m045"], report)
    return paths
