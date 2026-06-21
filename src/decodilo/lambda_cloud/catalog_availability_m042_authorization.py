"""Future-only M042 authorization for catalog-backed availability selection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_authorization_package import (
    LambdaAvailabilityFirstArtifactRef,
    load_lambda_availability_first_authorization_package,
)
from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    load_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.availability_first_go_no_go import (
    load_lambda_availability_first_go_no_go,
)
from decodilo.lambda_cloud.availability_first_launch_plan import (
    load_lambda_availability_first_launch_plan,
)
from decodilo.lambda_cloud.capacity_error_closeout import (
    load_lambda_capacity_error_closeout,
)
from decodilo.lambda_cloud.catalog_availability_operator_decision import (
    load_lambda_catalog_availability_operator_decision,
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

LambdaCatalogAvailabilityM042AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m042_catalog_availability_launch_review",
]


class LambdaCatalogAvailabilityM042Authorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaCatalogAvailabilityM042AuthorizationStatus
    capacity_closeout_ref: LambdaAvailabilityFirstArtifactRef
    availability_authorization_ref: LambdaAvailabilityFirstArtifactRef
    go_no_go_ref: LambdaAvailabilityFirstArtifactRef
    risk_acceptance_ref: LambdaAvailabilityFirstArtifactRef
    operator_decision_ref: LambdaAvailabilityFirstArtifactRef
    response_loss_controls_ref: LambdaAvailabilityFirstArtifactRef
    selected_candidate: str | None = None
    candidate_source: str | None = None
    live_availability_status: str | None = None
    estimated_30min_cost: float | None = None
    buffered_30min_cost: float | None = None
    selected_ssh_key_hash: str | None = None
    risk_acceptance_status: str
    operator_decision_status: str
    effective_launch_timeout_seconds: float | None = None
    response_capture_active: bool = False
    no_auto_launch_retry: bool = False
    launch_authorized_for_next_milestone: bool
    launch_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaCatalogAvailabilityM042Authorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M042 authorization cannot authorize launch now")
        if self.launch_authorized_for_next_milestone and self.blockers:
            raise ValueError("M042 authorization cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_availability_m042_authorization_from_paths(
    *,
    capacity_closeout: str | Path,
    availability_authorization: str | Path,
    go_no_go: str | Path,
    risk_acceptance: str | Path,
    operator_decision: str | Path,
    response_loss_controls: str | Path,
) -> LambdaCatalogAvailabilityM042Authorization:
    blockers: list[str] = []
    closeout = load_lambda_capacity_error_closeout(capacity_closeout)
    availability = load_lambda_availability_first_authorization_package(
        availability_authorization
    )
    go = load_lambda_availability_first_go_no_go(go_no_go)
    risk = load_lambda_catalog_availability_risk_acceptance(risk_acceptance)
    decision = load_lambda_catalog_availability_operator_decision(operator_decision)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    if not closeout.closeout_succeeded:
        blockers.extend(closeout.blockers or ["capacity_error_closeout_not_succeeded"])
    if (
        availability.authorization_status
        != "authorized_for_future_availability_first_launch_review"
    ):
        blockers.extend(availability.blockers or ["availability_authorization_not_passed"])
    if go.status != "go_for_future_availability_first_launch_review":
        blockers.extend(go.blockers or ["availability_first_go_no_go_not_passed"])
    if (
        risk.acceptance_status != "accepted_for_future_m042_review"
        or not risk.acceptance_complete_for_m042_review
    ):
        blockers.extend(risk.blockers or ["catalog_availability_risk_not_accepted"])
    if (
        decision.decision_status
        != "accept_catalog_availability_risk_for_future_m042_review"
    ):
        blockers.extend(decision.blockers or ["operator_decision_does_not_accept_risk"])
    if not controls.controls_passed:
        blockers.extend(controls.blockers or ["response_loss_controls_failed"])
    if not controls.no_auto_launch_retry:
        blockers.append("automatic_launch_retry_enabled")

    selected_candidate = None
    candidate_source = None
    live_status = None
    estimated = None
    buffered = None
    selected_ssh_hash = None
    try:
        rank = load_lambda_availability_first_candidate_ranker(availability.rank_ref.path)
        if rank.selected_candidate is None:
            blockers.append("availability_rank_has_no_selected_candidate")
        else:
            selected_candidate = rank.selected_candidate.shape
            candidate_source = rank.selected_candidate.source
            live_status = (
                "live_available"
                if rank.selected_candidate.live_available
                else "endpoint_inconclusive"
            )
            estimated = rank.selected_candidate.estimated_30min_cost
            buffered = rank.selected_candidate.buffered_estimated_30min_cost
            if rank.selected_candidate.shape != "gpu_1x_h100_pcie":
                blockers.append("selected_candidate_not_gpu_1x_h100_pcie")
            if buffered is None or buffered >= 50.0:
                blockers.append("selected_candidate_buffered_cost_not_below_50")
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"availability_rank_unreadable: {exc}")
    try:
        plan = load_lambda_availability_first_launch_plan(availability.plan_ref.path)
        if not plan.plan_passed or plan.plan is None:
            blockers.extend(plan.blockers or ["availability_first_plan_not_passed"])
        elif plan.plan.selected_shape != "gpu_1x_h100_pcie":
            blockers.append("availability_plan_shape_not_gpu_1x_h100_pcie")
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"availability_plan_unreadable: {exc}")
    if availability.ssh_key_selection_ref is None:
        blockers.append("ssh_key_selection_ref_missing")
    else:
        try:
            ssh = load_lambda_existing_ssh_key_selection(
                availability.ssh_key_selection_ref.path
            )
            selected_ssh_hash = ssh.selected_ssh_key_name_redacted_or_hash
            if not ssh.selection_passed:
                blockers.extend(ssh.errors or ["ssh_key_selection_failed"])
            if not selected_ssh_hash:
                blockers.append("selected_ssh_key_hash_missing")
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"ssh_key_selection_unreadable: {exc}")

    blockers = sorted(set(blockers))
    authorized = not blockers
    return LambdaCatalogAvailabilityM042Authorization(
        authorization_status=(
            "authorized_for_future_m042_catalog_availability_launch_review"
            if authorized
            else "not_authorized"
        ),
        capacity_closeout_ref=_ref(capacity_closeout),
        availability_authorization_ref=_ref(availability_authorization),
        go_no_go_ref=_ref(go_no_go),
        risk_acceptance_ref=_ref(risk_acceptance),
        operator_decision_ref=_ref(operator_decision),
        response_loss_controls_ref=_ref(response_loss_controls),
        selected_candidate=selected_candidate,
        candidate_source=candidate_source,
        live_availability_status=live_status,
        estimated_30min_cost=estimated,
        buffered_30min_cost=buffered,
        selected_ssh_key_hash=selected_ssh_hash,
        risk_acceptance_status=risk.acceptance_status,
        operator_decision_status=decision.decision_status,
        effective_launch_timeout_seconds=controls.timeout_seconds,
        response_capture_active=controls.response_capture_active,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        launch_authorized_for_next_milestone=authorized,
        blockers=blockers,
        warnings=[
            "M042 authorization is future-review only; it does not authorize launch now",
            "catalog-only availability may still return another capacity error",
        ],
    )


def _ref(path: str | Path) -> LambdaAvailabilityFirstArtifactRef:
    target = Path(path)
    return LambdaAvailabilityFirstArtifactRef(
        path=str(target),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    )


def load_lambda_catalog_availability_m042_authorization(
    path: str | Path,
) -> LambdaCatalogAvailabilityM042Authorization:
    return LambdaCatalogAvailabilityM042Authorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_availability_m042_authorization(
    path: str | Path,
    report: LambdaCatalogAvailabilityM042Authorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
