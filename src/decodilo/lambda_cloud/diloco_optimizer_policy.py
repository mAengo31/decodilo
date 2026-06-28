"""Future bounded DiLoCo optimizer-fidelity policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    load_lambda_diloco_optimizer_command_discovery,
)

LambdaDilocoOptimizerPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaDilocoOptimizerPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082A"
    policy_status: LambdaDilocoOptimizerPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_bounded_optimizer_fidelity_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    max_steps: int = 1
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_real_training: bool = True
    no_background_process: bool = True
    must_not_overclaim_full_training: bool = True
    must_truthfully_report_optimizer_semantics: bool = True
    halt_after_first_failed_live_stage: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaDilocoOptimizerPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo optimizer policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing DiLoCo optimizer policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_optimizer_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaDilocoOptimizerPolicy:
    discovery = load_lambda_diloco_optimizer_command_discovery(command_discovery)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_diloco_optimizer_command":
        blockers.append("no_safe_diloco_optimizer_command_found")
    if not discovery.argv_tokens:
        blockers.append("diloco_optimizer_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("diloco_optimizer_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("diloco_optimizer_not_synthetic")
    if discovery.inner_optimizer != "adamw":
        blockers.append("inner_optimizer_not_adamw")
    if discovery.outer_optimizer != "nesterov":
        blockers.append("outer_optimizer_not_nesterov")
    if discovery.expected_optimizer_fidelity != "optimizer_semantics_smoke":
        blockers.append("optimizer_semantics_smoke_not_expected")
    if discovery.max_steps != 1:
        blockers.append("diloco_optimizer_max_steps_not_one")
    if not discovery.pseudo_gradient_semantics_required:
        blockers.append("pseudo_gradient_semantics_not_required")
    if not discovery.persistent_optimizer_state_required:
        blockers.append("persistent_optimizer_state_not_required")
    if not discovery.deterministic_reference_check_required:
        blockers.append("deterministic_reference_check_not_required")
    if not discovery.no_external_network:
        blockers.append("diloco_optimizer_network_allowed")
    if not discovery.no_downloads:
        blockers.append("diloco_optimizer_download_allowed")
    if not discovery.no_package_install:
        blockers.append("diloco_optimizer_package_install_allowed")
    if not discovery.no_real_training:
        blockers.append("diloco_optimizer_training_allowed")
    if not discovery.no_background_process:
        blockers.append("diloco_optimizer_background_allowed")
    if discovery.gpu_required:
        blockers.append("diloco_optimizer_gpu_required")
    safe = not blockers
    return LambdaDilocoOptimizerPolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_bounded_optimizer_fidelity_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        inner_optimizer=discovery.inner_optimizer,
        outer_optimizer=discovery.outer_optimizer,
        max_steps=discovery.max_steps,
        blockers=blockers,
        warnings=[
            "policy is future-only; M083R requires fresh gates and operator approval",
        ],
    )


def load_lambda_diloco_optimizer_policy(
    path: str | Path,
) -> LambdaDilocoOptimizerPolicy:
    return LambdaDilocoOptimizerPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_optimizer_policy(
    path: str | Path,
    report: LambdaDilocoOptimizerPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
