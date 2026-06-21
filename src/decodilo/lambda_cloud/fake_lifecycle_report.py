"""Combined report for fake Lambda lifecycle rehearsal."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_state import FakeLambdaLifecycleState


class FakeLambdaLifecycleReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    fake_lifecycle_id: str
    fake_only: bool = True
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    fake_mutating_operations: int = 0
    billable_action_performed: bool = False
    launch_plan_ref: str
    teardown_plan_ref: str | None = None
    m020_report_ref: str | None = None
    approval_manifest_ref: str | None = None
    lifecycle_journal_ref: str
    lifecycle_state: FakeLambdaLifecycleState
    fake_resources_created: int = 0
    fake_resources_terminated: int = 0
    fake_orphans_detected: int = 0
    unmanaged_live_resources_detected: int = 0
    health_check_summary: dict = Field(default_factory=dict)
    teardown_verification: dict = Field(default_factory=dict)
    idempotency_summary: dict = Field(default_factory=dict)
    failure_injection_summary: dict = Field(default_factory=dict)
    manual_review_required: bool = False
    fake_lifecycle_passed: bool = False
    future_real_launch_candidate: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_fake_lambda_lifecycle_report(path: str | Path) -> FakeLambdaLifecycleReport:
    return FakeLambdaLifecycleReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_fake_lambda_lifecycle_report(
    path: str | Path,
    report: FakeLambdaLifecycleReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

