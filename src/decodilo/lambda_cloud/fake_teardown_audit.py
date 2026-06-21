"""Audit fake Lambda teardown evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_report import load_fake_lambda_lifecycle_report


class FakeLambdaTeardownAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    fake_resources_total: int
    terminal_fake_resources: int
    non_terminal_fake_resources: int
    failed_terminate_resources: list[str] = Field(default_factory=list)
    fake_orphan_candidates: list[str] = Field(default_factory=list)
    live_read_only_resources_modified: bool = False
    no_real_termination_commands_generated: bool = True
    teardown_idempotency_verified: bool
    journal_contains_terminate_events: bool
    lifecycle_state_and_ledger_agree: bool
    manual_review_required: bool
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_fake_lambda_teardown(
    *,
    lifecycle_report: str | Path,
    teardown_report: str | Path,
) -> FakeLambdaTeardownAuditReport:
    original = load_fake_lambda_lifecycle_report(lifecycle_report)
    teardown = load_fake_lambda_lifecycle_report(teardown_report)
    resources = list(teardown.lifecycle_state.resources.values())
    non_terminal = [record.resource_id for record in resources if record.state != "terminated"]
    failed = [record.resource_id for record in resources if record.state == "failed_terminate"]
    journal_path = Path(teardown.lifecycle_journal_ref)
    journal_text = journal_path.read_text(encoding="utf-8") if journal_path.exists() else ""
    contains_terminate = "fake_terminate_started" in journal_text
    idempotent = teardown.fake_resources_terminated >= original.fake_resources_terminated
    agree = teardown.fake_resources_terminated == sum(
        1 for record in resources if record.state == "terminated"
    )
    errors: list[str] = []
    if non_terminal:
        errors.append("fake teardown left non-terminal synthetic resources")
    if not contains_terminate:
        errors.append("fake teardown journal lacks terminate events")
    if not agree:
        errors.append("fake lifecycle state and teardown counters disagree")
    return FakeLambdaTeardownAuditReport(
        passed=not errors,
        fake_resources_total=len(resources),
        terminal_fake_resources=len(resources) - len(non_terminal),
        non_terminal_fake_resources=len(non_terminal),
        failed_terminate_resources=failed,
        fake_orphan_candidates=non_terminal,
        teardown_idempotency_verified=idempotent,
        journal_contains_terminate_events=contains_terminate,
        lifecycle_state_and_ledger_agree=agree,
        manual_review_required=bool(errors),
        errors=errors,
    )


def write_fake_lambda_teardown_audit_report(
    path: str | Path,
    report: FakeLambdaTeardownAuditReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
