"""Stress runner for fake Lambda lifecycle rehearsal."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_launch_executor import (
    FakeLifecycleConfig,
    execute_fake_lambda_launch,
)
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_mutation_contract import (
    evaluate_fake_lambda_mutation_contract,
)
from decodilo.lambda_cloud.fake_orphan_detector import detect_fake_lambda_orphans
from decodilo.lambda_cloud.fake_teardown_audit import audit_fake_lambda_teardown
from decodilo.lambda_cloud.fake_teardown_executor import execute_fake_lambda_teardown
from decodilo.lambda_cloud.fake_termination_verifier import verify_fake_lambda_termination


class FakeLambdaLifecycleStressReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    cycles_requested: int
    cycles_completed: int
    cycles_failed: int
    fake_resources_created: int
    fake_resources_terminated: int
    fake_orphans_detected: int
    recoverable_failures: int
    unrecoverable_failures: int
    journal_replay_passed: bool
    teardown_verification_passed: bool
    mutation_contract_passed: bool
    manual_review_required: bool = False
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    cycle_reports: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_fake_lambda_lifecycle_stress(
    *,
    m020_report: str | Path,
    approval_manifest: str | Path,
    workdir: str | Path,
    cycles: int,
    failure_modes: list[str],
) -> FakeLambdaLifecycleStressReport:
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    completed = 0
    failed = 0
    created = 0
    terminated = 0
    orphans = 0
    recoverable = 0
    unrecoverable = 0
    journal_ok = True
    verify_ok = True
    contract_ok = True
    manual_review = False
    cycle_reports: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []
    modes = failure_modes or ["none"]
    for cycle in range(cycles):
        mode = modes[cycle % len(modes)]
        launch_failure_mode = (
            "duplicate_launch_request" if mode == "duplicate_launch_request" else mode
        )
        cycle_dir = root / f"cycle-{cycle:03d}"
        idempotency_key = f"fake-stress-{cycle:03d}"
        launch = execute_fake_lambda_launch(
            m020_report_path=m020_report,
            approval_manifest_path=approval_manifest,
            workdir=cycle_dir,
            idempotency_key=idempotency_key,
            config=FakeLifecycleConfig(
                failure=FakeLambdaFailureConfig(failure_mode=launch_failure_mode)
            ),
        )
        if mode == "duplicate_launch_request":
            launch = execute_fake_lambda_launch(
                m020_report_path=m020_report,
                approval_manifest_path=approval_manifest,
                workdir=cycle_dir,
                idempotency_key=idempotency_key,
            )
        launch_path = cycle_dir / "launch-report.json"
        launch_path.write_text(launch.to_json(), encoding="utf-8")
        teardown_failure = (
            FakeLambdaFailureConfig(failure_mode=mode)
            if mode in {"partial_terminate_failure", "terminate_timeout"}
            else FakeLambdaFailureConfig()
        )
        teardown = execute_fake_lambda_teardown(
            lifecycle_report_path=launch_path,
            failure=teardown_failure,
        )
        teardown_path = cycle_dir / "teardown-report.json"
        teardown_path.write_text(teardown.to_json(), encoding="utf-8")
        verification = verify_fake_lambda_termination(teardown)
        orphan_report = detect_fake_lambda_orphans(teardown)
        contract = evaluate_fake_lambda_mutation_contract(teardown)
        teardown_audit = audit_fake_lambda_teardown(
            lifecycle_report=launch_path,
            teardown_report=teardown_path,
        )
        completed += 1
        created += teardown.fake_resources_created
        terminated += teardown.fake_resources_terminated
        orphans += orphan_report.fake_orphan_count
        cycle_failed = not (verification.passed and contract.passed and teardown_audit.passed)
        failed += int(cycle_failed)
        recoverable += int(teardown.manual_review_required)
        unrecoverable += int(bool(teardown.errors))
        has_expected_state = bool(
            teardown.lifecycle_state.resources or mode == "fail_before_launch_commit"
        )
        journal_ok = journal_ok and has_expected_state
        verify_ok = verify_ok and verification.passed
        contract_ok = contract_ok and contract.passed
        manual_review = manual_review or teardown.manual_review_required
        cycle_reports.append(
            {
                "cycle": cycle,
                "failure_mode": mode,
                "fake_resources_created": teardown.fake_resources_created,
                "fake_resources_terminated": teardown.fake_resources_terminated,
                "manual_review_required": teardown.manual_review_required,
                "verification_passed": verification.passed,
                "mutation_contract_passed": contract.passed,
                "teardown_audit_passed": teardown_audit.passed,
            }
        )
        errors.extend(teardown.errors)
        warnings.extend(teardown.warnings)
    return FakeLambdaLifecycleStressReport(
        cycles_requested=cycles,
        cycles_completed=completed,
        cycles_failed=failed,
        fake_resources_created=created,
        fake_resources_terminated=terminated,
        fake_orphans_detected=orphans,
        recoverable_failures=recoverable,
        unrecoverable_failures=unrecoverable,
        journal_replay_passed=journal_ok,
        teardown_verification_passed=verify_ok,
        mutation_contract_passed=contract_ok,
        manual_review_required=manual_review,
        cycle_reports=cycle_reports,
        warnings=warnings,
        errors=errors,
    )


def write_fake_lambda_lifecycle_stress_report(
    path: str | Path,
    report: FakeLambdaLifecycleStressReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
