"""Close out the successful Lambda lifecycle smoke."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lifecycle_smoke_evidence_package import (
    load_lambda_lifecycle_smoke_evidence_package,
)
from decodilo.lambda_cloud.lifecycle_smoke_postrun_reconciliation import (
    load_lambda_lifecycle_smoke_postrun_reconciliation,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    load_lambda_lifecycle_smoke_success_record,
)

LambdaLifecycleSmokeCloseoutStatus = Literal[
    "closed_success",
    "closed_with_warnings",
    "unresolved",
]


class LambdaLifecycleSmokeCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    closeout_status: LambdaLifecycleSmokeCloseoutStatus
    closeout_succeeded: bool
    final_instance_count: int
    final_unmanaged_count: int
    termination_verified: bool
    manual_review_required: bool
    secret_scan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLifecycleSmokeCloseout:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lifecycle smoke closeout cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lifecycle_smoke_closeout_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
) -> LambdaLifecycleSmokeCloseout:
    success = load_lambda_lifecycle_smoke_success_record(success_record)
    reconcile = load_lambda_lifecycle_smoke_postrun_reconciliation(reconciliation)
    evidence = load_lambda_lifecycle_smoke_evidence_package(evidence_package)
    blockers = [*success.blockers, *reconcile.errors, *evidence.blockers]
    if success.status != "lifecycle_smoke_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("postrun_reconciliation_not_passed")
    if not evidence.evidence_complete:
        blockers.append("evidence_package_incomplete")
    if not success.secret_scan_passed:
        blockers.append("secret_scan_not_passed")
    if success.final_instance_count != 0 or success.final_unmanaged_count != 0:
        blockers.append("final_visible_or_unmanaged_instances_present")
    closeout_status: LambdaLifecycleSmokeCloseoutStatus
    if blockers:
        closeout_status = "unresolved"
    elif evidence.warnings or success.warnings or reconcile.warnings:
        closeout_status = "closed_with_warnings"
    else:
        closeout_status = "closed_success"
    return LambdaLifecycleSmokeCloseout(
        closeout_status=closeout_status,
        closeout_succeeded=not blockers,
        final_instance_count=success.final_instance_count,
        final_unmanaged_count=success.final_unmanaged_count,
        termination_verified=success.termination_verified,
        manual_review_required=success.manual_review_required,
        secret_scan_passed=success.secret_scan_passed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "closeout is read-only",
                    *success.warnings,
                    *reconcile.warnings,
                    *evidence.warnings,
                ]
            )
        ),
    )


def load_lambda_lifecycle_smoke_closeout(path: str | Path) -> LambdaLifecycleSmokeCloseout:
    return LambdaLifecycleSmokeCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lifecycle_smoke_closeout(
    path: str | Path,
    report: LambdaLifecycleSmokeCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
