"""Fake Lambda orphan detection."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_report import (
    FakeLambdaLifecycleReport,
    load_fake_lambda_lifecycle_report,
)


class FakeLambdaOrphanDetectionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    fake_orphan_count: int
    fake_orphan_resource_ids: list[str] = Field(default_factory=list)
    unmanaged_live_count: int = 0
    manual_review_required: bool = False
    no_mutations_performed: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def detect_fake_lambda_orphans(
    report: FakeLambdaLifecycleReport,
) -> FakeLambdaOrphanDetectionReport:
    orphan_ids = [
        record.resource_id
        for record in report.lifecycle_state.resources.values()
        if record.state not in {"terminated"}
    ]
    unmanaged = report.unmanaged_live_resources_detected
    warnings = []
    if orphan_ids:
        warnings.append("fake resources remain non-terminal")
    if unmanaged:
        warnings.append("unmanaged live resources require manual review; no mutation performed")
    return FakeLambdaOrphanDetectionReport(
        fake_orphan_count=len(orphan_ids),
        fake_orphan_resource_ids=orphan_ids,
        unmanaged_live_count=unmanaged,
        manual_review_required=bool(orphan_ids or unmanaged),
        warnings=warnings,
    )


def detect_fake_lambda_orphans_from_path(path: str | Path) -> FakeLambdaOrphanDetectionReport:
    return detect_fake_lambda_orphans(load_fake_lambda_lifecycle_report(path))

