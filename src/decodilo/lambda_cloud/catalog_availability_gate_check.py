"""Gate check for future M042 catalog-availability launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_launch_plan import (
    load_lambda_availability_first_launch_plan,
)
from decodilo.lambda_cloud.catalog_availability_m042_authorization import (
    load_lambda_catalog_availability_m042_authorization,
)
from decodilo.lambda_cloud.catalog_availability_risk_acceptance import (
    load_lambda_catalog_availability_risk_acceptance,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)


class LambdaCatalogAvailabilityGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    candidate_source: str | None = None
    live_availability_status: str | None = None
    risk_acceptance_status: str
    effective_launch_timeout_seconds: float | None = None
    response_capture_active: bool
    no_auto_launch_retry: bool
    selected_ssh_key_hash: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogAvailabilityGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog availability gate check cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_availability_gate_check_from_paths(
    *,
    m042_authorization: str | Path,
    availability_plan: str | Path,
    risk_acceptance: str | Path,
    response_loss_controls: str | Path,
    ssh_key_selection: str | Path,
) -> LambdaCatalogAvailabilityGateCheck:
    auth = load_lambda_catalog_availability_m042_authorization(m042_authorization)
    plan = load_lambda_availability_first_launch_plan(availability_plan)
    risk = load_lambda_catalog_availability_risk_acceptance(risk_acceptance)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    blockers: list[str] = []
    if (
        auth.authorization_status
        != "authorized_for_future_m042_catalog_availability_launch_review"
    ):
        blockers.extend(auth.blockers or ["m042_authorization_not_passed"])
    if not plan.plan_passed or plan.plan is None:
        blockers.extend(plan.blockers or ["availability_first_plan_not_passed"])
    elif plan.plan.selected_shape != "gpu_1x_h100_pcie":
        blockers.append("availability_plan_shape_not_gpu_1x_h100_pcie")
    if risk.acceptance_status != "accepted_for_future_m042_review":
        blockers.extend(risk.blockers or ["catalog_availability_risk_not_accepted"])
    if not controls.controls_passed:
        blockers.extend(controls.blockers or ["response_loss_controls_failed"])
    if not controls.no_auto_launch_retry:
        blockers.append("automatic_launch_retry_enabled")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["ssh_key_selection_failed"])
    if not ssh.selected_ssh_key_name_redacted_or_hash:
        blockers.append("selected_ssh_key_hash_missing")
    blockers = sorted(set(blockers))
    return LambdaCatalogAvailabilityGateCheck(
        gate_passed=not blockers,
        selected_candidate=auth.selected_candidate,
        candidate_source=auth.candidate_source,
        live_availability_status=auth.live_availability_status,
        risk_acceptance_status=risk.acceptance_status,
        effective_launch_timeout_seconds=controls.timeout_seconds,
        response_capture_active=controls.response_capture_active,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        blockers=blockers,
        warnings=[
            "catalog availability gate check is future-review only",
            "catalog-only availability requires separate M042 operator supervision",
        ],
    )


def load_lambda_catalog_availability_gate_check(
    path: str | Path,
) -> LambdaCatalogAvailabilityGateCheck:
    return LambdaCatalogAvailabilityGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_availability_gate_check(
    path: str | Path,
    report: LambdaCatalogAvailabilityGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
