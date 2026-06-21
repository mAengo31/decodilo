"""Resource ownership and orphan-risk review for M025."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.m020_report import LambdaM020ReadinessReport, load_lambda_m020_report
from decodilo.lambda_cloud.mutation_resource_scope import (
    LambdaMutationResourceScope,
    load_lambda_mutation_resource_scope,
)


class LambdaResourceOwnershipReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_schema_version: int = 1
    review_id: str = "lambda-resource-ownership-review-m025"
    m020_report_ref: str
    resource_scope_ref: str | None = None
    unmanaged_billable_resources: int
    planned_owned_resources: int
    terminate_unowned_allowed: bool
    resource_ownership_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaResourceOwnershipReport = LambdaResourceOwnershipReview


def review_lambda_resource_ownership(
    *,
    m020_report: str | Path | LambdaM020ReadinessReport,
    resource_scope: str | Path | LambdaMutationResourceScope | None = None,
) -> LambdaResourceOwnershipReview:
    report, report_ref = _load_m020(m020_report)
    scope, scope_ref = _load_scope(resource_scope)
    blockers: list[str] = []
    ledger_count = report.resource_reconciliation.unmanaged_billable_instances
    if ledger_count:
        blockers.append("unmanaged billable resources present")
    if not report.resource_reconciliation.resource_reconciliation_passed:
        blockers.append("resource reconciliation did not pass")
    if scope is None:
        blockers.append("mutation resource scope missing")
        planned_owned = 0
        terminate_unowned = False
    else:
        planned_owned = len(scope.owned_scope.owned_resource_ids)
        terminate_unowned = scope.terminate_unowned_allowed
        if scope.unowned_live_resource_ids:
            blockers.append("unowned live resources appear in mutation scope")
        if scope.terminate_unowned_allowed:
            blockers.append("terminate-unowned is allowed")
    return LambdaResourceOwnershipReview(
        m020_report_ref=report_ref,
        resource_scope_ref=scope_ref,
        unmanaged_billable_resources=ledger_count,
        planned_owned_resources=planned_owned,
        terminate_unowned_allowed=terminate_unowned,
        resource_ownership_passed=not blockers,
        blockers=blockers,
        warnings=["Ownership review is advisory and cannot enable launch."],
    )


def _load_m020(
    value: str | Path | LambdaM020ReadinessReport,
) -> tuple[LambdaM020ReadinessReport, str]:
    if isinstance(value, LambdaM020ReadinessReport):
        return value, "<in-memory>"
    return load_lambda_m020_report(value), str(value)


def _load_scope(
    value: str | Path | LambdaMutationResourceScope | None,
) -> tuple[LambdaMutationResourceScope | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, LambdaMutationResourceScope):
        return value, "<in-memory>"
    return load_lambda_mutation_resource_scope(value), str(value)


def load_lambda_resource_ownership_review(path: str | Path) -> LambdaResourceOwnershipReview:
    return LambdaResourceOwnershipReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_resource_ownership_review(
    path: str | Path,
    review: LambdaResourceOwnershipReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(review.to_json(), encoding="utf-8")
