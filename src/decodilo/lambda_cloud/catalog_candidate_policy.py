"""Policy for catalog-backed Lambda candidate rotation after capacity errors."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaCatalogCandidatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    exclude_recent_capacity_error_shapes: bool = True
    allow_operator_override_for_failed_shape: bool = False
    prefer_lower_cost_single_gpu: bool = True
    max_budget: float = 50.0
    planned_hours: float = 0.5
    safety_buffer_multiplier: float = 1.15
    quantity: int = 1
    require_existing_ssh_key: bool = True
    no_filesystem_required: bool = True
    no_setup_cloud_init_training: bool = True
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogCandidatePolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog candidate policy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def default_lambda_catalog_candidate_policy(
    *,
    allow_operator_override_for_failed_shape: bool = False,
    max_budget: float = 50.0,
) -> LambdaCatalogCandidatePolicy:
    return LambdaCatalogCandidatePolicy(
        allow_operator_override_for_failed_shape=allow_operator_override_for_failed_shape,
        max_budget=max_budget,
        warnings=[
            "catalog candidate policy is future-review only",
            "recent capacity-error shapes are excluded by default",
        ],
    )


def load_lambda_catalog_candidate_policy(path: str | Path) -> LambdaCatalogCandidatePolicy:
    return LambdaCatalogCandidatePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_candidate_policy(
    path: str | Path,
    report: LambdaCatalogCandidatePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
