"""Resource-scope model for disabled Lambda mutation skeleton review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m020_report import (
    LambdaM020ReadinessReport,
    load_lambda_m020_report,
)


class LambdaOwnedResourceScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope_id: str = "planned-owned-placeholder"
    owned_resource_ids: list[str] = Field(default_factory=lambda: ["planned-owned-placeholder"])
    owned_resource_source: str = "review_only_placeholder"
    review_only: bool = True


class LambdaMutationResourceScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    owned_scope: LambdaOwnedResourceScope = Field(default_factory=LambdaOwnedResourceScope)
    unowned_live_resource_ids: list[str] = Field(default_factory=list)
    terminate_unowned_allowed: bool = False
    real_owned_resource_ids_present: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_scope(self) -> LambdaMutationResourceScope:
        overlap = set(self.owned_scope.owned_resource_ids).intersection(
            self.unowned_live_resource_ids
        )
        if overlap:
            raise ValueError("unowned live resources cannot be in owned mutation scope")
        if self.terminate_unowned_allowed:
            raise ValueError("terminate_unowned is forbidden")
        if self.real_owned_resource_ids_present:
            raise ValueError("M024 must not contain real owned mutation resource ids")
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("resource scope cannot enable Lambda mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaResourceScopeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    resource_scope: LambdaMutationResourceScope
    scope_valid_for_review: bool
    scope_valid_for_execution: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_mutation_resource_scope(
    *,
    m020_report: str | Path | LambdaM020ReadinessReport,
) -> LambdaMutationResourceScope:
    report = (
        m020_report
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else load_lambda_m020_report(m020_report)
    )
    unmanaged = report.resource_reconciliation.unmanaged_summary.unmanaged_instance_ids
    return LambdaMutationResourceScope(
        run_id=Path(report.launch_plan_ref).stem or "lambda-run",
        unowned_live_resource_ids=unmanaged,
        warnings=["Scope uses review-only placeholder ownership in M024."],
    )


def evaluate_lambda_mutation_resource_scope(
    scope: LambdaMutationResourceScope,
) -> LambdaResourceScopeReport:
    return LambdaResourceScopeReport(
        resource_scope=scope,
        scope_valid_for_review=True,
        warnings=["Resource scope is not valid for execution in M024."],
    )


def load_lambda_mutation_resource_scope(path: str | Path) -> LambdaMutationResourceScope:
    return LambdaMutationResourceScope.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_mutation_resource_scope(
    path: str | Path,
    scope: LambdaMutationResourceScope,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(scope.to_json(), encoding="utf-8")
