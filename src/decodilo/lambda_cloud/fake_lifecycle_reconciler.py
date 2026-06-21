"""Fake Lambda lifecycle reconciliation report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_report import (
    FakeLambdaLifecycleReport,
    load_fake_lambda_lifecycle_report,
)
from decodilo.lambda_cloud.fake_orphan_detector import (
    FakeLambdaOrphanDetectionReport,
    detect_fake_lambda_orphans,
)


class FakeLambdaLifecycleReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    planned_fake_resources: int
    fake_created_resources: int
    fake_terminated_resources: int
    fake_orphan_count: int
    unmanaged_live_count: int
    manual_review_required: bool
    no_mutations_performed: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_fake_lambda_lifecycle(
    report: FakeLambdaLifecycleReport,
) -> FakeLambdaLifecycleReconciliationReport:
    orphan_report: FakeLambdaOrphanDetectionReport = detect_fake_lambda_orphans(report)
    return FakeLambdaLifecycleReconciliationReport(
        planned_fake_resources=report.fake_resources_created,
        fake_created_resources=report.fake_resources_created,
        fake_terminated_resources=report.fake_resources_terminated,
        fake_orphan_count=orphan_report.fake_orphan_count,
        unmanaged_live_count=orphan_report.unmanaged_live_count,
        manual_review_required=orphan_report.manual_review_required,
        warnings=orphan_report.warnings,
    )


def reconcile_fake_lambda_lifecycle_from_path(
    path: str | Path,
) -> FakeLambdaLifecycleReconciliationReport:
    return reconcile_fake_lambda_lifecycle(load_fake_lambda_lifecycle_report(path))

