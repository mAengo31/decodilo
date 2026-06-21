from __future__ import annotations

from pathlib import Path

from lambda_m040_helpers import write_m040_inputs

from decodilo.lambda_cloud.catalog_availability_command_preview import (
    build_lambda_catalog_availability_command_preview_from_paths,
    write_lambda_catalog_availability_command_preview,
)
from decodilo.lambda_cloud.catalog_availability_gate_check import (
    build_lambda_catalog_availability_gate_check_from_paths,
    write_lambda_catalog_availability_gate_check,
)
from decodilo.lambda_cloud.catalog_availability_m042_authorization import (
    build_lambda_catalog_availability_m042_authorization_from_paths,
    write_lambda_catalog_availability_m042_authorization,
)
from decodilo.lambda_cloud.catalog_availability_operator_decision import (
    build_lambda_catalog_availability_operator_decision,
    write_lambda_catalog_availability_operator_decision,
)
from decodilo.lambda_cloud.catalog_availability_risk_acceptance import (
    build_lambda_catalog_availability_risk_acceptance,
    write_lambda_catalog_availability_risk_acceptance,
)
from decodilo.lambda_cloud.m041_report import (
    build_lambda_m041_report_from_paths,
)
from decodilo.lambda_cloud.wait_for_live_availability_plan import (
    build_lambda_wait_for_live_availability_plan,
    write_lambda_wait_for_live_availability_plan,
)


def accepted_risk():
    return build_lambda_catalog_availability_risk_acceptance(
        accept_risk=True,
        acknowledge_all=True,
    )


def declined_risk():
    return build_lambda_catalog_availability_risk_acceptance(decline_risk=True)


def accepted_decision():
    return build_lambda_catalog_availability_operator_decision(accepted_risk())


def declined_decision():
    return build_lambda_catalog_availability_operator_decision(declined_risk())


def write_m041_inputs(tmp_path: Path, *, accepted: bool = True) -> dict[str, Path]:
    paths = write_m040_inputs(tmp_path)
    paths.update(
        {
            "risk": tmp_path / "risk.json",
            "decision": tmp_path / "decision.json",
            "m042": tmp_path / "m042.json",
            "gate": tmp_path / "gate.json",
            "preview": tmp_path / "preview.json",
            "wait": tmp_path / "wait.json",
            "m041": tmp_path / "m041.json",
        }
    )
    risk = accepted_risk() if accepted else declined_risk()
    write_lambda_catalog_availability_risk_acceptance(paths["risk"], risk)
    decision = build_lambda_catalog_availability_operator_decision(risk)
    write_lambda_catalog_availability_operator_decision(paths["decision"], decision)
    if accepted:
        auth = build_lambda_catalog_availability_m042_authorization_from_paths(
            capacity_closeout=paths["closeout"],
            availability_authorization=paths["authorization"],
            go_no_go=paths["go"],
            risk_acceptance=paths["risk"],
            operator_decision=paths["decision"],
            response_loss_controls=paths["controls"],
        )
        write_lambda_catalog_availability_m042_authorization(paths["m042"], auth)
        gate = build_lambda_catalog_availability_gate_check_from_paths(
            m042_authorization=paths["m042"],
            availability_plan=paths["plan"],
            risk_acceptance=paths["risk"],
            response_loss_controls=paths["controls"],
            ssh_key_selection=paths["ssh"],
        )
        write_lambda_catalog_availability_gate_check(paths["gate"], gate)
        preview = build_lambda_catalog_availability_command_preview_from_paths(
            m042_authorization=paths["m042"],
            gate_check=paths["gate"],
        )
        write_lambda_catalog_availability_command_preview(paths["preview"], preview)
        report = build_lambda_m041_report_from_paths(
            risk_acceptance=paths["risk"],
            operator_decision=paths["decision"],
            m042_authorization=paths["m042"],
            gate_check=paths["gate"],
            command_preview=paths["preview"],
        )
    else:
        auth = build_lambda_catalog_availability_m042_authorization_from_paths(
            capacity_closeout=paths["closeout"],
            availability_authorization=paths["authorization"],
            go_no_go=paths["go"],
            risk_acceptance=paths["risk"],
            operator_decision=paths["decision"],
            response_loss_controls=paths["controls"],
        )
        write_lambda_catalog_availability_m042_authorization(paths["m042"], auth)
        wait = build_lambda_wait_for_live_availability_plan(decision)
        write_lambda_wait_for_live_availability_plan(paths["wait"], wait)
        report = build_lambda_m041_report_from_paths(
            risk_acceptance=paths["risk"],
            operator_decision=paths["decision"],
            wait_plan=paths["wait"],
        )
    paths["m041"].write_text(report.to_json(), encoding="utf-8")
    return paths
