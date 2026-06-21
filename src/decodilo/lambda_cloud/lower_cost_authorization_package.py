"""Lower-cost Strand-compatible future authorization package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_price_reconciliation import (
    load_lambda_lower_cost_price_reconciliation,
)
from decodilo.lambda_cloud.lower_cost_resource_reconciliation import (
    load_lambda_lower_cost_resource_reconciliation,
)
from decodilo.lambda_cloud.strand_cli_compatibility import (
    load_strand_cli_compatibility_report,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    load_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)

LambdaLowerCostAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_lower_cost_launch_review",
]


class LambdaLowerCostAuthorizationArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaLowerCostAuthorizationPackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_plan_ref: LambdaLowerCostAuthorizationArtifactRef
    ssh_key_selection_ref: LambdaLowerCostAuthorizationArtifactRef
    price_reconciliation_ref: LambdaLowerCostAuthorizationArtifactRef
    resource_reconciliation_ref: LambdaLowerCostAuthorizationArtifactRef
    strand_compatibility_ref: LambdaLowerCostAuthorizationArtifactRef
    response_loss_controls_ref: LambdaLowerCostAuthorizationArtifactRef
    operator_acknowledgement_required_for_future_launch: bool = True
    future_authorization_status: LambdaLowerCostAuthorizationStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostAuthorizationPackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost authorization package cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_authorization_package(
    *,
    launch_plan: str | Path,
    ssh_key_selection: str | Path,
    price_reconciliation: str | Path,
    resource_reconciliation: str | Path,
    strand_compatibility: str | Path,
    response_loss_controls: str | Path,
) -> LambdaLowerCostAuthorizationPackage:
    blockers: list[str] = []
    launch = load_lambda_strand_lower_cost_launch_plan_report(launch_plan)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    price = load_lambda_lower_cost_price_reconciliation(price_reconciliation)
    resource = load_lambda_lower_cost_resource_reconciliation(resource_reconciliation)
    strand = load_strand_cli_compatibility_report(strand_compatibility)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    if not launch.plan_passed:
        blockers.extend(launch.blockers or ["lower_cost_launch_plan_failed"])
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_failed"])
    if not price.price_reconciliation_passed:
        blockers.extend(price.errors or ["lower_cost_price_reconciliation_failed"])
    if not resource.resource_reconciliation_passed:
        blockers.extend(resource.errors or ["lower_cost_resource_reconciliation_failed"])
    if strand.compatibility_status != "compatible":
        blockers.append("strand_compatibility_not_compatible")
    if not controls.controls_passed:
        blockers.extend(controls.blockers or ["strand_response_loss_controls_failed"])
    return LambdaLowerCostAuthorizationPackage(
        launch_plan_ref=_artifact_ref(launch_plan),
        ssh_key_selection_ref=_artifact_ref(ssh_key_selection),
        price_reconciliation_ref=_artifact_ref(price_reconciliation),
        resource_reconciliation_ref=_artifact_ref(resource_reconciliation),
        strand_compatibility_ref=_artifact_ref(strand_compatibility),
        response_loss_controls_ref=_artifact_ref(response_loss_controls),
        future_authorization_status=(
            "authorized_for_future_lower_cost_launch_review"
            if not blockers
            else "not_authorized"
        ),
        blockers=blockers,
        warnings=[
            "authorization is for future review only",
            "M037R does not authorize immediate launch execution",
        ],
    )


def _artifact_ref(path: str | Path) -> LambdaLowerCostAuthorizationArtifactRef:
    target = Path(path)
    return LambdaLowerCostAuthorizationArtifactRef(
        path=str(target),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    )


def load_lambda_lower_cost_authorization_package(
    path: str | Path,
) -> LambdaLowerCostAuthorizationPackage:
    return LambdaLowerCostAuthorizationPackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_authorization_package(
    path: str | Path,
    report: LambdaLowerCostAuthorizationPackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
