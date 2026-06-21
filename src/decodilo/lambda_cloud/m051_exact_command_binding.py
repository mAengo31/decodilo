"""Bind M051 one-shot arming to the exact future execution command."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_one_shot_arming import (
    DEFAULT_M051_WORKDIR,
    LambdaM051OneShotArming,
    load_lambda_m051_one_shot_arming,
)

M051_OPERATOR_CONFIRMATION_BILLABLE = (
    "I understand this may create a billable Lambda instance and must be terminated"
)
M051_OPERATOR_CONFIRMATION_TERMINATE = (
    "I understand this run must terminate the owned instance and verify termination"
)

_REQUIRED_FLAGS = [
    "--m051-bootstrap-authorization",
    "--m051-metadata-plan",
    "--m051-bootstrap-execution-gate-check",
    "--m051-no-mutation-no-ssh-audit",
    "--m051-bootstrap-runbook-preview",
    "--m050-report",
    "--m051-one-shot-arming",
    "--m051-reviewer-bridge",
    "--m051-artifact-binding",
    "--m051-arming-gate",
    "--ssh-key-selection",
    "--response-loss-controls",
]

_FORBIDDEN_FLAGS = [
    "--ssh",
    "--ssh-command",
    "--remote-command",
    "--setup-script",
    "--cloud-init",
    "--user-data",
    "--train",
    "--package-install",
]


class LambdaM051ExactCommandBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    binding_passed: bool
    command_preview: list[str] = Field(default_factory=list)
    command_hash: str | None = None
    command_contains_required_flags: bool
    command_contains_forbidden_flags: bool = False
    executable: bool = False
    workdir: str = DEFAULT_M051_WORKDIR
    selected_candidate: str | None = None
    selected_region: str | None = None
    no_ssh: bool = True
    no_remote_commands: bool = True
    no_training: bool = True
    no_package_install: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaM051ExactCommandBinding:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_ssh
            or not self.no_remote_commands
            or not self.no_training
            or not self.no_package_install
        ):
            raise ValueError("M051 command binding must remain non-executable and safe")
        if self.binding_passed and (
            self.blockers or self.command_contains_forbidden_flags
        ):
            raise ValueError("M051 command binding cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_exact_command_binding_from_paths(
    *,
    arming: str | Path,
) -> LambdaM051ExactCommandBinding:
    return build_lambda_m051_exact_command_binding(
        arming=load_lambda_m051_one_shot_arming(arming),
        arming_path=str(arming),
    )


def build_lambda_m051_exact_command_binding(
    *,
    arming: LambdaM051OneShotArming,
    arming_path: str,
) -> LambdaM051ExactCommandBinding:
    command = _m051b_command_preview(arming_path=arming_path, workdir=arming.workdir)
    text_items = set(command)
    missing_flags = [flag for flag in _REQUIRED_FLAGS if flag not in text_items]
    forbidden = [flag for flag in _FORBIDDEN_FLAGS if flag in text_items]
    blockers: list[str] = []
    if arming.arming_status != "armed_for_one_shot_m051_metadata_bootstrap":
        blockers.extend(arming.blockers or ["m051_one_shot_arming_not_armed"])
    if missing_flags:
        blockers.extend(f"missing_required_flag:{flag}" for flag in missing_flags)
    if forbidden:
        blockers.extend(f"forbidden_flag_present:{flag}" for flag in forbidden)
    if arming.workdir != DEFAULT_M051_WORKDIR:
        blockers.append("unexpected_m051_workdir")
    digest = hashlib.sha256(
        json.dumps(command, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return LambdaM051ExactCommandBinding(
        binding_passed=not blockers,
        command_preview=command,
        command_hash=digest,
        command_contains_required_flags=not missing_flags,
        command_contains_forbidden_flags=bool(forbidden),
        workdir=arming.workdir,
        selected_candidate=arming.selected_candidate,
        selected_region=arming.selected_region,
        blockers=sorted(set(blockers)),
        warnings=[
            "command preview is hash-bound but non-executable in M051A",
            "raw SSH key name is not included in the preview",
        ],
    )


def _m051b_command_preview(*, arming_path: str, workdir: str) -> list[str]:
    return [
        "python",
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--env-file",
        ".env",
        "--env-key",
        "LAMBDA_API_KEY",
        "--m051-bootstrap-authorization",
        "/tmp/decodilo-lambda-m051-bootstrap-authorization.json",
        "--m051-metadata-plan",
        "/tmp/decodilo-lambda-m051-metadata-bootstrap-plan.json",
        "--m051-bootstrap-execution-gate-check",
        "/tmp/decodilo-lambda-m051-bootstrap-execution-gate-check.json",
        "--m051-no-mutation-no-ssh-audit",
        "/tmp/decodilo-lambda-m051-no-mutation-no-ssh-audit.json",
        "--m051-bootstrap-runbook-preview",
        "/tmp/decodilo-lambda-m051-bootstrap-runbook-preview.json",
        "--m050-report",
        "/tmp/decodilo-lambda-m050-report.json",
        "--m051-one-shot-arming",
        arming_path,
        "--m051-reviewer-bridge",
        "/tmp/decodilo-lambda-m051-reviewer-bridge.json",
        "--m051-artifact-binding",
        "/tmp/decodilo-lambda-m051-artifact-binding.json",
        "--m051-arming-gate",
        "/tmp/decodilo-lambda-m051-arming-gate-check.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--workdir",
        workdir,
        "--execute-real-launch",
        "--confirm-billable-action",
        M051_OPERATOR_CONFIRMATION_BILLABLE,
        "--confirm-terminate-required",
        M051_OPERATOR_CONFIRMATION_TERMINATE,
    ]


def load_lambda_m051_exact_command_binding(
    path: str | Path,
) -> LambdaM051ExactCommandBinding:
    return LambdaM051ExactCommandBinding.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_exact_command_binding(
    path: str | Path,
    report: LambdaM051ExactCommandBinding,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
