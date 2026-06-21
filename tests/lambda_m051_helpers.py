from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lambda_m037r_helpers import controls
from lambda_m047_helpers import SUCCESS_REGION, SUCCESS_SHAPE
from lambda_m050_helpers import write_m050_inputs

from decodilo.lambda_cloud.api_models import LambdaInstanceType, LambdaSSHKey
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m051_arming_command_preview import (
    build_lambda_m051_arming_command_preview_from_paths,
    write_lambda_m051_arming_command_preview,
)
from decodilo.lambda_cloud.m051_arming_gate_check import (
    build_lambda_m051_arming_gate_check_from_paths,
    write_lambda_m051_arming_gate_check,
)
from decodilo.lambda_cloud.m051_artifact_binding import (
    build_lambda_m051_artifact_binding_from_paths,
    write_lambda_m051_artifact_binding,
)
from decodilo.lambda_cloud.m051_bootstrap_execution_gate import (
    build_lambda_m051_bootstrap_execution_gate_from_paths,
    write_lambda_m051_bootstrap_execution_gate,
)
from decodilo.lambda_cloud.m051_exact_command_binding import (
    build_lambda_m051_exact_command_binding_from_paths,
    write_lambda_m051_exact_command_binding,
)
from decodilo.lambda_cloud.m051_execution_reviewer_bridge import (
    build_lambda_m051_execution_reviewer_bridge_from_paths,
    write_lambda_m051_execution_reviewer_bridge,
)
from decodilo.lambda_cloud.m051_metadata_bootstrap_plan import (
    build_lambda_m051_metadata_bootstrap_plan_from_paths,
    write_lambda_m051_metadata_bootstrap_plan,
)
from decodilo.lambda_cloud.m051_no_mutation_no_ssh_audit import (
    build_lambda_m051_no_mutation_no_ssh_audit_from_paths,
    write_lambda_m051_no_mutation_no_ssh_audit,
)
from decodilo.lambda_cloud.m051_one_shot_arming import (
    build_lambda_m051_one_shot_arming_from_paths,
    write_lambda_m051_one_shot_arming,
)
from decodilo.lambda_cloud.m051_operator_confirmation import (
    build_lambda_m051_operator_confirmation,
    write_lambda_m051_operator_confirmation,
)
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    write_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    select_existing_lambda_ssh_key,
    write_lambda_existing_ssh_key_selection,
)

RAW_TEST_SSH_KEY_NAME = "existing-key"


def m051_discovery(*, include_candidate: bool = True) -> LambdaLiveDiscoveryReport:
    return LambdaLiveDiscoveryReport(
        source="live_read_only",
        live_api_used=True,
        ssh_keys=[
            LambdaSSHKey(
                key_id=RAW_TEST_SSH_KEY_NAME,
                name=RAW_TEST_SSH_KEY_NAME,
                metadata={"public_key_redacted": True},
            )
        ],
        instance_types=[
            LambdaInstanceType(
                instance_type_id=SUCCESS_SHAPE,
                name=SUCCESS_SHAPE,
                gpu_type="A100 80GB SXM4",
                gpus=8,
                price_per_hour=22.32,
                regions=[SUCCESS_REGION],
            )
        ]
        if include_candidate
        else [],
        required_endpoint_success=True,
        secret_redacted=True,
    )


def write_m051_inputs(
    base: Path,
    *,
    include_candidate: bool = True,
) -> dict[str, Path]:
    paths = write_m050_inputs(base / "m050")
    paths.update(
        {
            "discovery_m051": base / "m051-discovery.json",
            "ssh_key_selection": base / "strand-ssh-key-selection.json",
            "controls": base / "strand-response-loss-controls.json",
            "metadata_plan": base / "m051-metadata-plan.json",
            "execution_gate": base / "m051-execution-gate.json",
            "audit_m051": base / "m051-no-mutation-no-ssh-audit.json",
            "operator_confirmation_m051": base / "m051-operator-confirmation.json",
            "one_shot_arming_m051": base / "m051-one-shot-arming.json",
            "command_binding_m051": base / "m051-command-binding.json",
            "artifact_binding_m051": base / "m051-artifact-binding.json",
            "reviewer_bridge_m051": base / "m051-reviewer-bridge.json",
            "arming_gate_m051": base / "m051-arming-gate.json",
            "arming_command_preview_m051": base / "m051-arming-command-preview.json",
        }
    )
    discovery = m051_discovery(include_candidate=include_candidate)
    write_lambda_live_discovery_report(paths["discovery_m051"], discovery)
    write_lambda_existing_ssh_key_selection(
        paths["ssh_key_selection"],
        select_existing_lambda_ssh_key(discovery=discovery),
    )
    write_lambda_strand_response_loss_control_check(paths["controls"], controls())
    plan = build_lambda_m051_metadata_bootstrap_plan_from_paths(
        discovery_report=paths["discovery_m051"],
        bootstrap_authorization=paths["authorization"],
        ssh_key_selection=paths["ssh_key_selection"],
        price_snapshot=paths["price_snapshot"],
        lifecycle_success_record=paths["success"],
        lifecycle_closeout=paths["closeout"],
    )
    write_lambda_m051_metadata_bootstrap_plan(paths["metadata_plan"], plan)
    gate = build_lambda_m051_bootstrap_execution_gate_from_paths(
        metadata_plan=paths["metadata_plan"],
        scope=paths["scope"],
        access_policy=paths["access"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
    )
    write_lambda_m051_bootstrap_execution_gate(paths["execution_gate"], gate)
    audit = build_lambda_m051_no_mutation_no_ssh_audit_from_paths(
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        m050_report=paths["m050"],
        ssh_key_selection=paths["ssh_key_selection"],
        public_artifacts=[
            paths["metadata_plan"],
            paths["execution_gate"],
            paths["m050"],
        ],
    )
    write_lambda_m051_no_mutation_no_ssh_audit(paths["audit_m051"], audit)
    confirmation = build_lambda_m051_operator_confirmation(
        confirm_metadata_only_bootstrap=True,
        acknowledge_all=True,
    )
    write_lambda_m051_operator_confirmation(
        paths["operator_confirmation_m051"],
        confirmation,
    )
    one_shot = build_lambda_m051_one_shot_arming_from_paths(
        operator_confirmation=paths["operator_confirmation_m051"],
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        no_mutation_no_ssh_audit=paths["audit_m051"],
        bootstrap_authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
        expires_minutes=15,
    )
    write_lambda_m051_one_shot_arming(paths["one_shot_arming_m051"], one_shot)
    command_binding = build_lambda_m051_exact_command_binding_from_paths(
        arming=paths["one_shot_arming_m051"],
    )
    write_lambda_m051_exact_command_binding(
        paths["command_binding_m051"],
        command_binding,
    )
    artifact_binding = build_lambda_m051_artifact_binding_from_paths(
        arming=paths["one_shot_arming_m051"],
        command_binding=paths["command_binding_m051"],
    )
    write_lambda_m051_artifact_binding(
        paths["artifact_binding_m051"],
        artifact_binding,
    )
    bridge = build_lambda_m051_execution_reviewer_bridge_from_paths(
        arming=paths["one_shot_arming_m051"],
        command_binding=paths["command_binding_m051"],
        artifact_binding=paths["artifact_binding_m051"],
    )
    write_lambda_m051_execution_reviewer_bridge(
        paths["reviewer_bridge_m051"],
        bridge,
    )
    arming_gate = build_lambda_m051_arming_gate_check_from_paths(
        reviewer_bridge=paths["reviewer_bridge_m051"],
    )
    write_lambda_m051_arming_gate_check(paths["arming_gate_m051"], arming_gate)
    arming_preview = build_lambda_m051_arming_command_preview_from_paths(
        arming_gate=paths["arming_gate_m051"],
    )
    write_lambda_m051_arming_command_preview(
        paths["arming_command_preview_m051"],
        arming_preview,
    )
    return paths


def m051_flag_args(paths: dict[str, Path], *, omit: set[str] | None = None) -> list[str]:
    pairs = [
        ("--m051-bootstrap-authorization", paths["authorization"]),
        ("--m051-metadata-plan", paths["metadata_plan"]),
        ("--m051-bootstrap-execution-gate-check", paths["execution_gate"]),
        ("--m051-no-mutation-no-ssh-audit", paths["audit_m051"]),
        ("--m051-bootstrap-runbook-preview", paths["runbook"]),
        ("--m050-report", paths["m050"]),
        ("--ssh-key-selection", paths["ssh_key_selection"]),
        ("--response-loss-controls", paths["controls"]),
        ("--m051-one-shot-arming", paths["one_shot_arming_m051"]),
        ("--m051-reviewer-bridge", paths["reviewer_bridge_m051"]),
        ("--m051-artifact-binding", paths["artifact_binding_m051"]),
        ("--m051-arming-gate", paths["arming_gate_m051"]),
    ]
    omitted = omit or set()
    args: list[str] = []
    for flag, path in pairs:
        if flag in omitted:
            continue
        args.extend([flag, str(path)])
    return args


def run_m051_fake(
    tmp_path: Path,
    *,
    omit: set[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    paths = write_m051_inputs(tmp_path / "artifacts")
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        *m051_flag_args(paths, omit=omit),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    result.paths = paths  # type: ignore[attr-defined]
    result.workdir = workdir  # type: ignore[attr-defined]
    return result


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
