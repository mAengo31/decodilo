"""Human approval manifest for future Lambda lifecycle work."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaApprovalStatus = Literal[
    "not_requested",
    "incomplete",
    "approved_for_future_fake_launch_lifecycle",
    "approved_for_future_real_launch_review",
    "rejected",
]


class LambdaOperatorAcknowledgements(BaseModel):
    model_config = ConfigDict(frozen=True)

    understands_billable_action: bool = False
    understands_termination_required: bool = False
    understands_budget_limit: bool = False
    understands_no_background_work: bool = False
    understands_no_production_training: bool = False
    understands_launch_not_enabled_yet: bool = False

    def missing(self) -> list[str]:
        return [name for name, value in self.model_dump().items() if value is not True]


class LambdaHumanApprovalManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_schema_version: int = 1
    approval_id: str
    created_at_utc: str | None = None
    operator_name: str | None = None
    operator_acknowledgements: LambdaOperatorAcknowledgements = Field(
        default_factory=LambdaOperatorAcknowledgements
    )
    approved_max_instances: int = Field(default=1, gt=0)
    approved_max_runtime_minutes: int = Field(default=30, gt=0)
    approved_max_budget: float = Field(default=50.0, ge=0)
    approved_instance_type: str
    approved_region: str
    approved_gpu_type: str
    approved_gpus_per_instance: int = Field(gt=0)
    approval_scope: list[str] = Field(default_factory=list)
    approval_notes: str = ""
    approval_status: LambdaApprovalStatus = "incomplete"
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _prevent_current_real_launch_review(self) -> LambdaHumanApprovalManifest:
        if self.approval_status == "approved_for_future_real_launch_review":
            raise ValueError("M020 must not produce approved_for_future_real_launch_review")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_approval_template(
    *,
    instance_type: str,
    region: str,
    gpu_type: str,
    gpus_per_instance: int,
    max_budget: float = 50.0,
    max_runtime_minutes: int = 30,
    approval_id: str = "lambda-approval-template",
) -> LambdaHumanApprovalManifest:
    return LambdaHumanApprovalManifest(
        approval_id=approval_id,
        approved_instance_type=instance_type,
        approved_region=region,
        approved_gpu_type=gpu_type,
        approved_gpus_per_instance=gpus_per_instance,
        approved_max_budget=max_budget,
        approved_max_runtime_minutes=max_runtime_minutes,
        approval_status="incomplete",
        approval_notes="Template only; does not enable Lambda launch.",
    )


def load_lambda_approval_manifest(path: str | Path) -> LambdaHumanApprovalManifest:
    return LambdaHumanApprovalManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_approval_manifest(path: str | Path, manifest: LambdaHumanApprovalManifest) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.to_json(), encoding="utf-8")
