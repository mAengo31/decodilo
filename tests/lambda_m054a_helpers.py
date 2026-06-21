from __future__ import annotations

from pathlib import Path

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m054a_report import (
    build_lambda_m054a_report_from_paths,
    write_lambda_m054a_report,
)
from decodilo.lambda_cloud.ssh_connectivity_command_preview import (
    build_lambda_ssh_connectivity_command_preview_from_paths,
    write_lambda_ssh_connectivity_command_preview,
)
from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    build_lambda_ssh_connectivity_execution_plan_from_path,
    write_lambda_ssh_connectivity_execution_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_no_exec_audit import (
    build_lambda_ssh_connectivity_no_exec_audit_from_paths,
    write_lambda_ssh_connectivity_no_exec_audit,
)
from decodilo.lambda_cloud.ssh_connectivity_one_shot_arming import (
    build_lambda_ssh_connectivity_one_shot_arming_from_paths,
    write_lambda_ssh_connectivity_one_shot_arming,
)
from decodilo.lambda_cloud.ssh_connectivity_reviewer_bridge import (
    build_lambda_ssh_connectivity_reviewer_bridge_from_paths,
    write_lambda_ssh_connectivity_reviewer_bridge,
)
from decodilo.lambda_cloud.ssh_connectivity_static_validator import (
    build_lambda_ssh_connectivity_static_validation_from_paths,
    write_lambda_ssh_connectivity_static_validation,
)
from decodilo.lambda_cloud.ssh_private_key_reference_policy import (
    build_lambda_ssh_private_key_reference_policy_from_path,
    write_lambda_ssh_private_key_reference_policy,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    build_lambda_ssh_safe_client_command_from_path,
    write_lambda_ssh_safe_client_command,
)


def write_m054a_inputs(base: Path) -> dict[str, Path]:
    paths = write_m053_inputs(base / "m053", approve=True)
    paths.update(
        {
            "execution_plan": base / "execution-plan.json",
            "private_key_policy": base / "private-key-policy.json",
            "safe_command": base / "safe-command.json",
            "static_validation": base / "static-validation.json",
            "one_shot_arming": base / "one-shot-arming.json",
            "reviewer_bridge": base / "reviewer-bridge.json",
            "no_exec_audit": base / "no-exec-audit.json",
            "command_preview": base / "command-preview.json",
            "m054a": base / "m054a.json",
        }
    )
    execution_plan = build_lambda_ssh_connectivity_execution_plan_from_path(
        paths["authorization"],
    )
    write_lambda_ssh_connectivity_execution_plan(paths["execution_plan"], execution_plan)
    private_key = build_lambda_ssh_private_key_reference_policy_from_path(
        paths["ssh_selection"],
    )
    write_lambda_ssh_private_key_reference_policy(paths["private_key_policy"], private_key)
    safe_command = build_lambda_ssh_safe_client_command_from_path(
        paths["private_key_policy"],
    )
    write_lambda_ssh_safe_client_command(paths["safe_command"], safe_command)
    static = build_lambda_ssh_connectivity_static_validation_from_paths(
        execution_plan=paths["execution_plan"],
        private_key_policy=paths["private_key_policy"],
        safe_client_command=paths["safe_command"],
    )
    write_lambda_ssh_connectivity_static_validation(paths["static_validation"], static)
    arming = build_lambda_ssh_connectivity_one_shot_arming_from_paths(
        execution_plan=paths["execution_plan"],
        static_validation=paths["static_validation"],
        authorization=paths["authorization"],
        expires_minutes=15,
    )
    write_lambda_ssh_connectivity_one_shot_arming(paths["one_shot_arming"], arming)
    bridge = build_lambda_ssh_connectivity_reviewer_bridge_from_paths(
        arming=paths["one_shot_arming"],
        static_validation=paths["static_validation"],
        safe_client_command=paths["safe_command"],
    )
    write_lambda_ssh_connectivity_reviewer_bridge(paths["reviewer_bridge"], bridge)
    audit = build_lambda_ssh_connectivity_no_exec_audit_from_paths(
        execution_plan=paths["execution_plan"],
        safe_client_command=paths["safe_command"],
    )
    write_lambda_ssh_connectivity_no_exec_audit(paths["no_exec_audit"], audit)
    preview = build_lambda_ssh_connectivity_command_preview_from_paths(
        reviewer_bridge=paths["reviewer_bridge"],
        no_exec_audit=paths["no_exec_audit"],
    )
    write_lambda_ssh_connectivity_command_preview(paths["command_preview"], preview)
    report = build_lambda_m054a_report_from_paths(
        execution_plan=paths["execution_plan"],
        static_validation=paths["static_validation"],
        reviewer_bridge=paths["reviewer_bridge"],
        no_exec_audit=paths["no_exec_audit"],
        command_preview=paths["command_preview"],
    )
    write_lambda_m054a_report(paths["m054a"], report)
    return paths
