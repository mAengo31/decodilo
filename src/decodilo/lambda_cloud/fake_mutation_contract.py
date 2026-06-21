"""Contract checks for fake Lambda mutation-shaped lifecycle evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_report import (
    FakeLambdaLifecycleReport,
    load_fake_lambda_lifecycle_report,
)


class FakeLambdaMutationContractReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    synthetic_ids_only: bool
    fake_only: bool
    real_lambda_api_used: bool
    real_mutating_operations: int
    billable_action_performed: bool
    idempotency_keys_present: bool
    journal_events_present: bool
    fake_mutation_api_events_present: bool
    teardown_verification_present: bool
    approval_ref_present: bool
    budget_gate_ref_present: bool
    resource_ledger_ref_present: bool
    no_executable_real_command_generated: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_fake_lambda_mutation_contract(
    report: FakeLambdaLifecycleReport,
) -> FakeLambdaMutationContractReport:
    errors: list[str] = []
    warnings: list[str] = []
    synthetic = all(
        record.resource_id.startswith(("fake-i-", "fake-key-", "fake-fs-"))
        for record in report.lifecycle_state.resources.values()
    )
    if not synthetic:
        errors.append("fake lifecycle contains non-synthetic resource id")
    if not report.fake_only:
        errors.append("fake lifecycle report must be fake_only=true")
    if report.real_lambda_api_used or report.real_mutating_operations:
        errors.append("fake lifecycle report contains real Lambda API mutation")
    if report.billable_action_performed:
        errors.append("fake lifecycle report contains billable action")
    idempotency_key = report.idempotency_summary.get("idempotency_key")
    idempotency_present = isinstance(idempotency_key, str) and bool(idempotency_key)
    if not idempotency_present:
        errors.append("fake lifecycle idempotency key missing")
    journal_path = Path(report.lifecycle_journal_ref)
    journal_text = journal_path.read_text(encoding="utf-8") if journal_path.exists() else ""
    journal_present = bool(journal_text.strip())
    if not journal_present:
        errors.append("fake lifecycle journal missing")
    mutation_events = "fake_mutation_api" in journal_text
    if not mutation_events:
        errors.append("fake mutation API event metadata missing from journal")
    teardown_present = bool(report.teardown_verification)
    if not teardown_present:
        warnings.append("teardown verification missing from current lifecycle report")
    approval_present = bool(report.approval_manifest_ref)
    if not approval_present:
        errors.append("approval manifest reference missing")
    budget_present = bool(report.m020_report_ref)
    if not budget_present:
        errors.append("M020 budget/readiness reference missing")
    resource_present = report.unmanaged_live_resources_detected >= 0
    if report.launch_allowed or report.launch_ready:
        errors.append("fake mutation contract requires launch flags false")
    return FakeLambdaMutationContractReport(
        passed=not errors,
        synthetic_ids_only=synthetic,
        fake_only=report.fake_only,
        real_lambda_api_used=report.real_lambda_api_used,
        real_mutating_operations=report.real_mutating_operations,
        billable_action_performed=report.billable_action_performed,
        idempotency_keys_present=idempotency_present,
        journal_events_present=journal_present,
        fake_mutation_api_events_present=mutation_events,
        teardown_verification_present=teardown_present,
        approval_ref_present=approval_present,
        budget_gate_ref_present=budget_present,
        resource_ledger_ref_present=resource_present,
        errors=errors,
        warnings=warnings,
    )


def evaluate_fake_lambda_mutation_contract_from_path(
    lifecycle_report: str | Path,
) -> FakeLambdaMutationContractReport:
    report = load_fake_lambda_lifecycle_report(lifecycle_report)
    return evaluate_fake_lambda_mutation_contract(report)


def write_fake_lambda_mutation_contract_report(
    path: str | Path,
    report: FakeLambdaMutationContractReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
