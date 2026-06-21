from __future__ import annotations

from pathlib import Path

from lambda_m037r_helpers import (
    controls,
    discovery,
    launch_plan,
    price_reconciliation,
    resource_reconciliation,
    ssh_selection,
)

from decodilo.lambda_cloud.live_discovery_report import write_lambda_live_discovery_report
from decodilo.lambda_cloud.lower_cost_budget_lock import (
    build_lambda_lower_cost_budget_lock,
    write_lambda_lower_cost_budget_lock,
)
from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    build_lambda_lower_cost_canonical_readiness,
    write_lambda_lower_cost_canonical_readiness,
)
from decodilo.lambda_cloud.lower_cost_execution_gate_check import (
    build_lambda_lower_cost_execution_gate_check,
    write_lambda_lower_cost_execution_gate_check,
)
from decodilo.lambda_cloud.lower_cost_final_state_snapshot import (
    build_lambda_lower_cost_final_state_snapshot,
    write_lambda_lower_cost_final_state_snapshot,
)
from decodilo.lambda_cloud.lower_cost_gate_check import (
    build_lambda_lower_cost_gate_check,
    write_lambda_lower_cost_gate_check,
)
from decodilo.lambda_cloud.lower_cost_launch_command_preview import (
    build_lambda_lower_cost_launch_command_preview,
    write_lambda_lower_cost_launch_command_preview,
)
from decodilo.lambda_cloud.lower_cost_launch_window_lock import (
    build_lambda_lower_cost_launch_window_lock,
    write_lambda_lower_cost_launch_window_lock,
)
from decodilo.lambda_cloud.lower_cost_m039_authorization import (
    build_lambda_lower_cost_m039_authorization,
    write_lambda_lower_cost_m039_authorization,
)
from decodilo.lambda_cloud.lower_cost_operator_approval import (
    build_lambda_lower_cost_operator_approval_template,
    write_lambda_lower_cost_operator_approval,
)
from decodilo.lambda_cloud.lower_cost_resource_lock import (
    build_lambda_lower_cost_resource_lock,
    write_lambda_lower_cost_resource_lock,
)
from decodilo.lambda_cloud.m038_report import build_lambda_m038_report
from decodilo.lambda_cloud.m038a_report import (
    build_lambda_m038a_report,
    write_lambda_m038a_report,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    write_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    write_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)


def canonical_readiness(sample_price: bool = False):
    return build_lambda_lower_cost_canonical_readiness(
        launch_plan=launch_plan(),
        ssh_key_selection=ssh_selection(),
        price_reconciliation=price_reconciliation(sample=sample_price),
        resource_reconciliation=resource_reconciliation(),
    )


def state_snapshot(unmanaged: tuple[str, ...] = ()):
    return build_lambda_lower_cost_final_state_snapshot(
        discovery=discovery(unmanaged=unmanaged),
        canonical_readiness=canonical_readiness(),
    )


def budget_lock():
    return build_lambda_lower_cost_budget_lock(canonical_readiness())


def resource_lock():
    return build_lambda_lower_cost_resource_lock(
        state_snapshot=state_snapshot(),
        launch_plan=launch_plan(),
        ssh_key_selection=ssh_selection(),
    )


def launch_window_lock():
    return build_lambda_lower_cost_launch_window_lock()


def operator_approval(*, complete: bool = False):
    return build_lambda_lower_cost_operator_approval_template(
        acknowledge_all=complete,
    )


def authorization(*, approval_complete: bool = False):
    return build_lambda_lower_cost_m039_authorization(
        canonical_readiness=canonical_readiness(),
        state_snapshot=state_snapshot(),
        budget_lock=budget_lock(),
        resource_lock=resource_lock(),
        launch_window_lock=launch_window_lock(),
        operator_approval=operator_approval(complete=approval_complete),
        response_loss_controls=controls(),
    )


def gate_check(*, approval_complete: bool = False):
    return build_lambda_lower_cost_gate_check(
        authorization=authorization(approval_complete=approval_complete),
        canonical_readiness=canonical_readiness(),
        response_loss_controls=controls(),
    )


def execution_gate_check(*, approval_complete: bool = False):
    return build_lambda_lower_cost_execution_gate_check(
        m039_authorization=authorization(approval_complete=approval_complete),
        canonical_readiness=canonical_readiness(),
        state_snapshot=state_snapshot(),
        budget_lock=budget_lock(),
        resource_lock=resource_lock(),
        launch_window_lock=launch_window_lock(),
        launch_plan=launch_plan(),
        ssh_key_selection=ssh_selection(),
        response_loss_controls=controls(),
    )


def command_preview(*, approval_complete: bool = False):
    return build_lambda_lower_cost_launch_command_preview(
        authorization=authorization(approval_complete=approval_complete),
    )


def m038_report(*, approval_complete: bool = False):
    return build_lambda_m038_report(
        authorization=authorization(approval_complete=approval_complete),
        gate_check=gate_check(approval_complete=approval_complete),
        command_preview=command_preview(approval_complete=approval_complete),
    )


def m038a_report(*, approval_complete: bool = False):
    return build_lambda_m038a_report(
        authorization=authorization(approval_complete=approval_complete),
        gate_check=gate_check(approval_complete=approval_complete),
        command_preview=command_preview(approval_complete=approval_complete),
        operator_approval=operator_approval(complete=approval_complete),
    )


def write_m038_inputs(tmp_path: Path, *, approval_complete: bool = True) -> dict[str, Path]:
    paths = {
        "discovery": tmp_path / "discovery.json",
        "ssh": tmp_path / "ssh.json",
        "plan": tmp_path / "plan.json",
        "price": tmp_path / "price.json",
        "resource": tmp_path / "resource.json",
        "readiness": tmp_path / "readiness.json",
        "snapshot": tmp_path / "snapshot.json",
        "budget": tmp_path / "budget.json",
        "resource_lock": tmp_path / "resource-lock.json",
        "window": tmp_path / "window.json",
        "approval": tmp_path / "approval.json",
        "controls": tmp_path / "controls.json",
        "authorization": tmp_path / "authorization.json",
        "gate": tmp_path / "gate.json",
        "execution_gate": tmp_path / "execution-gate.json",
        "command": tmp_path / "command.json",
        "m038a": tmp_path / "m038a.json",
    }
    write_lambda_live_discovery_report(paths["discovery"], discovery())
    write_lambda_existing_ssh_key_selection(paths["ssh"], ssh_selection())
    write_lambda_strand_lower_cost_launch_plan_report(paths["plan"], launch_plan())
    write_lambda_lower_cost_canonical_readiness(paths["readiness"], canonical_readiness())
    write_lambda_lower_cost_final_state_snapshot(paths["snapshot"], state_snapshot())
    write_lambda_lower_cost_budget_lock(paths["budget"], budget_lock())
    write_lambda_lower_cost_resource_lock(paths["resource_lock"], resource_lock())
    write_lambda_lower_cost_launch_window_lock(paths["window"], launch_window_lock())
    write_lambda_lower_cost_operator_approval(
        paths["approval"],
        operator_approval(complete=approval_complete),
    )
    write_lambda_strand_response_loss_control_check(paths["controls"], controls())
    write_lambda_lower_cost_m039_authorization(
        paths["authorization"],
        authorization(approval_complete=approval_complete),
    )
    write_lambda_lower_cost_gate_check(
        paths["gate"],
        gate_check(approval_complete=approval_complete),
    )
    write_lambda_lower_cost_execution_gate_check(
        paths["execution_gate"],
        execution_gate_check(approval_complete=approval_complete),
    )
    write_lambda_lower_cost_launch_command_preview(
        paths["command"],
        command_preview(approval_complete=approval_complete),
    )
    write_lambda_m038a_report(
        paths["m038a"],
        m038a_report(approval_complete=approval_complete),
    )
    return paths
