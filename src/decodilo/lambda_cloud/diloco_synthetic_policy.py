"""Future bounded DiLoCo-shaped synthetic experiment safety policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    load_lambda_diloco_synthetic_command_discovery,
)

LambdaDilocoSyntheticPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaDilocoSyntheticPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080"
    policy_status: LambdaDilocoSyntheticPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_bounded_diloco_synthetic_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    learners: int = 1
    sync_rounds: int = 1
    max_steps: int = 1
    one_learner_default: bool = True
    one_syncer_role_default: bool = True
    one_sync_update_round_default: bool = True
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_real_training: bool = True
    no_background_process: bool = True
    halt_after_first_failed_live_stage: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaDilocoSyntheticPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo synthetic policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing DiLoCo synthetic policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_synthetic_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaDilocoSyntheticPolicy:
    discovery = load_lambda_diloco_synthetic_command_discovery(command_discovery)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_diloco_synthetic_command":
        blockers.append("no_safe_diloco_synthetic_command_found")
    if not discovery.argv_tokens:
        blockers.append("diloco_synthetic_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("diloco_synthetic_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("diloco_synthetic_not_synthetic")
    if not discovery.one_learner_default:
        blockers.append("diloco_synthetic_not_one_learner")
    if not discovery.one_syncer_role_default:
        blockers.append("diloco_synthetic_not_one_syncer_role")
    if not discovery.one_sync_update_round_default:
        blockers.append("diloco_synthetic_not_one_sync_update_round")
    if discovery.learners != 1:
        blockers.append("diloco_synthetic_learners_not_one")
    if discovery.sync_rounds != 1:
        blockers.append("diloco_synthetic_sync_rounds_not_one")
    if discovery.max_steps != 1:
        blockers.append("diloco_synthetic_max_steps_not_one")
    if not discovery.no_external_network:
        blockers.append("diloco_synthetic_network_allowed")
    if not discovery.no_downloads:
        blockers.append("diloco_synthetic_download_allowed")
    if not discovery.no_package_install:
        blockers.append("diloco_synthetic_package_install_allowed")
    if not discovery.no_real_training:
        blockers.append("diloco_synthetic_training_allowed")
    if not discovery.no_background_process:
        blockers.append("diloco_synthetic_background_allowed")
    if discovery.gpu_required:
        blockers.append("diloco_synthetic_gpu_required")
    safe = not blockers
    return LambdaDilocoSyntheticPolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_bounded_diloco_synthetic_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        learners=discovery.learners,
        sync_rounds=discovery.sync_rounds,
        max_steps=discovery.max_steps,
        blockers=blockers,
        warnings=[
            "policy is future-only; M081R requires fresh gates and operator approval",
        ],
    )


def load_lambda_diloco_synthetic_policy(
    path: str | Path,
) -> LambdaDilocoSyntheticPolicy:
    return LambdaDilocoSyntheticPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_synthetic_policy(
    path: str | Path,
    report: LambdaDilocoSyntheticPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
