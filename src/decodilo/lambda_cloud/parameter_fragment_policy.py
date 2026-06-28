"""Future bounded parameter-fragment synthetic policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    load_lambda_parameter_fragment_command_discovery,
)

LambdaParameterFragmentPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaParameterFragmentPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086A"
    policy_status: LambdaParameterFragmentPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_bounded_parameter_fragment_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    fragments: int = 2
    max_steps: int = 1
    expected_parameter_fragment_semantics: str | None = None
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_real_training: bool = True
    no_background_process: bool = True
    truthful_fragment_semantics_required: bool = True
    no_overlap_or_quantization_claim_unless_active: bool = True
    halt_after_first_failed_live_stage: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaParameterFragmentPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("parameter-fragment policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing parameter-fragment policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_parameter_fragment_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaParameterFragmentPolicy:
    discovery = load_lambda_parameter_fragment_command_discovery(command_discovery)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_parameter_fragment_command":
        blockers.append("no_safe_parameter_fragment_command_found")
    if not discovery.argv_tokens:
        blockers.append("parameter_fragment_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("parameter_fragment_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("parameter_fragment_not_synthetic")
    if discovery.fragments != 2:
        blockers.append("parameter_fragment_count_not_two")
    if discovery.max_steps != 1:
        blockers.append("parameter_fragment_max_steps_not_one")
    if not discovery.deterministic_fragment_definition_required:
        blockers.append("fragment_definition_not_required")
    if not discovery.fragment_update_required:
        blockers.append("fragment_update_not_required")
    if not discovery.fragment_schedule_required:
        blockers.append("fragment_schedule_not_required")
    if not discovery.per_fragment_version_state_required:
        blockers.append("per_fragment_state_not_required")
    if not discovery.merge_replay_validation_required:
        blockers.append("merge_replay_validation_not_required")
    if discovery.expected_parameter_fragment_semantics != "synthetic_vector_fragments":
        blockers.append("parameter_fragment_smoke_not_verified")
    if discovery.overlap_claim_allowed:
        blockers.append("overlap_claim_allowed_without_implementation")
    if discovery.quantization_claim_allowed:
        blockers.append("quantization_claim_allowed_without_implementation")
    if not discovery.no_external_network:
        blockers.append("parameter_fragment_network_allowed")
    if not discovery.no_downloads:
        blockers.append("parameter_fragment_download_allowed")
    if not discovery.no_package_install:
        blockers.append("parameter_fragment_package_install_allowed")
    if not discovery.no_real_training:
        blockers.append("parameter_fragment_training_allowed")
    if not discovery.no_background_process:
        blockers.append("parameter_fragment_background_allowed")
    if discovery.gpu_required:
        blockers.append("parameter_fragment_gpu_required")
    safe = not blockers
    return LambdaParameterFragmentPolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_bounded_parameter_fragment_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        fragments=discovery.fragments,
        max_steps=discovery.max_steps,
        expected_parameter_fragment_semantics=(
            discovery.expected_parameter_fragment_semantics
        ),
        blockers=blockers,
        warnings=[
            "policy is future-only; M087R requires fresh gates and operator approval",
        ],
    )


def load_lambda_parameter_fragment_policy(path: str | Path) -> LambdaParameterFragmentPolicy:
    return LambdaParameterFragmentPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_parameter_fragment_policy(
    path: str | Path,
    report: LambdaParameterFragmentPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
