from __future__ import annotations

from pathlib import Path

from lambda_m035_helpers import price_snapshot
from lambda_m037r_helpers import controls, ssh_selection
from lambda_m040_helpers import candidates

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    rank_lambda_availability_first_candidates,
    write_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.flexible_selector_authorization import (
    build_lambda_flexible_selector_authorization_from_paths,
    write_lambda_flexible_selector_authorization,
)
from decodilo.lambda_cloud.flexible_selector_command_preview import (
    build_lambda_flexible_selector_command_preview_from_paths,
    write_lambda_flexible_selector_command_preview,
)
from decodilo.lambda_cloud.flexible_selector_fixed_shape_audit import (
    build_lambda_flexible_selector_fixed_shape_audit_from_path,
    write_lambda_flexible_selector_fixed_shape_audit,
)
from decodilo.lambda_cloud.flexible_selector_gate_check import (
    build_lambda_flexible_selector_gate_check_from_paths,
    write_lambda_flexible_selector_gate_check,
)
from decodilo.lambda_cloud.flexible_selector_operator_approval import (
    build_lambda_flexible_selector_operator_approval,
    write_lambda_flexible_selector_operator_approval,
)
from decodilo.lambda_cloud.m044g_report import (
    build_lambda_m044g_report_from_paths,
    write_lambda_m044g_report,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    write_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import write_price_snapshot


def write_m044g_inputs(
    tmp_path: Path,
    *,
    approve: bool = True,
    acknowledge: bool = True,
    risk_accepted: bool = True,
    live: bool = False,
    missing_ssh: bool = False,
) -> dict[str, Path]:
    paths = {
        "prices": tmp_path / "prices.json",
        "ssh": tmp_path / "ssh.json",
        "controls": tmp_path / "controls.json",
        "selector_no_risk": tmp_path / "selector-no-risk.json",
        "selector_risk": tmp_path / "selector-risk.json",
        "approval": tmp_path / "approval.json",
        "authorization": tmp_path / "authorization.json",
        "gate": tmp_path / "gate.json",
        "audit": tmp_path / "audit.json",
        "preview": tmp_path / "preview.json",
        "report": tmp_path / "m044g.json",
    }
    write_price_snapshot(paths["prices"], price_snapshot())
    ssh = ssh_selection(ssh_key_names=() if missing_ssh else ("existing-key",))
    write_lambda_existing_ssh_key_selection(paths["ssh"], ssh)
    write_lambda_strand_response_loss_control_check(paths["controls"], controls())
    no_risk = rank_lambda_availability_first_candidates(
        candidates=candidates(live=live),
        ssh_key_selection=ssh,
    )
    write_lambda_availability_first_candidate_ranker(paths["selector_no_risk"], no_risk)
    with_risk = rank_lambda_availability_first_candidates(
        candidates=candidates(live=live),
        ssh_key_selection=ssh,
        catalog_only_risk_accepted=risk_accepted,
    )
    write_lambda_availability_first_candidate_ranker(paths["selector_risk"], with_risk)
    approval = build_lambda_flexible_selector_operator_approval(
        approve_future_review=approve,
        acknowledge_all=acknowledge,
    )
    write_lambda_flexible_selector_operator_approval(paths["approval"], approval)
    authorization = build_lambda_flexible_selector_authorization_from_paths(
        selector_output=paths["selector_risk"],
        operator_approval=paths["approval"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
        price_snapshot=paths["prices"],
    )
    write_lambda_flexible_selector_authorization(paths["authorization"], authorization)
    gate = build_lambda_flexible_selector_gate_check_from_paths(
        authorization=paths["authorization"],
        selector_output=paths["selector_risk"],
    )
    write_lambda_flexible_selector_gate_check(paths["gate"], gate)
    audit = build_lambda_flexible_selector_fixed_shape_audit_from_path(
        paths["authorization"]
    )
    write_lambda_flexible_selector_fixed_shape_audit(paths["audit"], audit)
    preview = build_lambda_flexible_selector_command_preview_from_paths(
        authorization=paths["authorization"],
        gate_check=paths["gate"],
        fixed_shape_audit=paths["audit"],
    )
    write_lambda_flexible_selector_command_preview(paths["preview"], preview)
    report = build_lambda_m044g_report_from_paths(
        selector_output=paths["selector_risk"],
        selector_without_risk=paths["selector_no_risk"],
        authorization=paths["authorization"],
        gate_check=paths["gate"],
        fixed_shape_audit=paths["audit"],
        command_preview=paths["preview"],
    )
    write_lambda_m044g_report(paths["report"], report)
    return paths
