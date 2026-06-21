"""Fake termination verification for synthetic Lambda resources."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_report import (
    FakeLambdaLifecycleReport,
    load_fake_lambda_lifecycle_report,
)


class FakeLambdaTerminationVerificationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    fake_resources_total: int
    fake_resources_terminated: int
    fake_orphan_candidates: int
    manual_review_required: bool
    no_real_termination_commands_generated: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def verify_fake_lambda_termination(
    report: FakeLambdaLifecycleReport,
) -> FakeLambdaTerminationVerificationReport:
    total = len(report.lifecycle_state.resources)
    terminated = sum(
        1 for record in report.lifecycle_state.resources.values() if record.state == "terminated"
    )
    orphans = sum(
        1
        for record in report.lifecycle_state.resources.values()
        if record.state not in {"terminated"}
    )
    errors = [] if orphans == 0 else ["fake resources remain non-terminal"]
    return FakeLambdaTerminationVerificationReport(
        passed=not errors,
        fake_resources_total=total,
        fake_resources_terminated=terminated,
        fake_orphan_candidates=orphans,
        manual_review_required=bool(errors),
        errors=errors,
    )


def verify_fake_lambda_termination_from_paths(
    *,
    lifecycle_report: str | Path,
    teardown_report: str | Path | None = None,
) -> FakeLambdaTerminationVerificationReport:
    report = load_fake_lambda_lifecycle_report(teardown_report or lifecycle_report)
    return verify_fake_lambda_termination(report)


def write_fake_lambda_termination_verification_report(
    path: str | Path,
    report: FakeLambdaTerminationVerificationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

