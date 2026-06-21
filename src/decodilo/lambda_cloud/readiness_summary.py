"""M020 Lambda readiness summary."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.launch_blockers import LambdaLaunchBlockerReport


class LambdaReadinessSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    m020_readiness_passed: bool
    future_fake_launch_lifecycle_candidate: bool
    future_real_launch_candidate: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_evidence: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_readiness_summary(
    *,
    blocker_report: LambdaLaunchBlockerReport,
    approval_passed_for_fake_lifecycle: bool,
) -> LambdaReadinessSummary:
    blocker_categories = [
        blocker.category for blocker in blocker_report.blockers if blocker.severity == "blocker"
    ]
    real_launch_invariant = {
        "launch_code_disabled",
        "launch_not_supported_in_current_milestone",
        "remote_backend_not_ready",
    }
    unresolved = [
        category for category in blocker_categories if category not in real_launch_invariant
    ]
    fake_candidate = approval_passed_for_fake_lifecycle and not unresolved
    next_evidence = []
    if "missing_human_approval" in blocker_categories:
        next_evidence.append("complete human approval manifest for future fake launch lifecycle")
    if "missing_budget_manifest" in blocker_categories:
        next_evidence.append("attach budget manifest")
    if (
        "missing_price_reconciliation" in blocker_categories
        or "price_missing" in blocker_categories
    ):
        next_evidence.append("complete price reconciliation")
    return LambdaReadinessSummary(
        m020_readiness_passed=fake_candidate,
        future_fake_launch_lifecycle_candidate=fake_candidate,
        blockers=blocker_categories,
        warnings=[
            blocker.message for blocker in blocker_report.blockers if blocker.severity == "warning"
        ],
        next_required_evidence=next_evidence,
    )


def load_lambda_readiness_summary(path: str | Path) -> LambdaReadinessSummary:
    return LambdaReadinessSummary.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_readiness_summary(path: str | Path, summary: LambdaReadinessSummary) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(summary.to_json(), encoding="utf-8")
