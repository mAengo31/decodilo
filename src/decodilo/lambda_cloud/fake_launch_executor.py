"""Fake Lambda launch executor with local-only state transitions."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.approval_manifest import load_lambda_approval_manifest
from decodilo.lambda_cloud.fake_health_checks import run_fake_lambda_health_check
from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_lifecycle_journal import FakeLambdaLifecycleJournal
from decodilo.lambda_cloud.fake_lifecycle_report import FakeLambdaLifecycleReport
from decodilo.lambda_cloud.fake_lifecycle_safety import validate_fake_lifecycle_safety
from decodilo.lambda_cloud.fake_lifecycle_state import make_fake_resource_id
from decodilo.lambda_cloud.fake_mutation_api import FakeLambdaMutationAPI
from decodilo.lambda_cloud.fake_mutation_models import FakeLambdaLaunchRequest
from decodilo.lambda_cloud.launch_plan import load_lambda_launch_plan
from decodilo.lambda_cloud.m020_report import load_lambda_m020_report


class FakeLifecycleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    fake_mode: bool = True
    failure: FakeLambdaFailureConfig = Field(default_factory=FakeLambdaFailureConfig)


def execute_fake_lambda_launch(
    *,
    m020_report_path: str | Path,
    approval_manifest_path: str | Path,
    workdir: str | Path,
    idempotency_key: str,
    config: FakeLifecycleConfig | None = None,
) -> FakeLambdaLifecycleReport:
    effective = config or FakeLifecycleConfig()
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    m020 = load_lambda_m020_report(m020_report_path)
    approval = load_lambda_approval_manifest(approval_manifest_path)
    launch_plan = load_lambda_launch_plan(m020.launch_plan_ref)
    lifecycle_id = _lifecycle_id(idempotency_key)
    journal_path = root / "fake_lifecycle.jsonl"
    journal = FakeLambdaLifecycleJournal(journal_path, lifecycle_id=lifecycle_id)
    replay = journal.replay()
    if replay.state.resources and effective.failure.failure_mode != "duplicate_launch_request":
        return _report_from_state(
            m020=m020,
            m020_report_path=m020_report_path,
            approval_manifest_path=approval_manifest_path,
            lifecycle_id=lifecycle_id,
            journal_path=journal_path,
            state=replay.state,
            idempotency_key=idempotency_key,
            warnings=["duplicate fake launch returned existing fake resources"],
        )
    safety = validate_fake_lifecycle_safety(
        m020_report=m020,
        approval_manifest=approval,
        launch_plan=launch_plan,
        fake_mode=effective.fake_mode,
    )
    if not safety.passed:
        journal.append(
            "fake_approval_gate_blocked",
            idempotency_key=idempotency_key,
            payload={"errors": safety.errors},
        )
        return _report_from_state(
            m020=m020,
            m020_report_path=m020_report_path,
            approval_manifest_path=approval_manifest_path,
            lifecycle_id=lifecycle_id,
            journal_path=journal_path,
            state=journal.replay().state,
            idempotency_key=idempotency_key,
            errors=safety.errors,
            warnings=safety.warnings,
        )
    if effective.failure.enabled("fail_before_launch_commit"):
        journal.append("fake_lifecycle_aborted", idempotency_key=idempotency_key)
        return _report_from_state(
            m020=m020,
            m020_report_path=m020_report_path,
            approval_manifest_path=approval_manifest_path,
            lifecycle_id=lifecycle_id,
            journal_path=journal_path,
            state=journal.replay().state,
            idempotency_key=idempotency_key,
            errors=["injected failure before fake launch commit"],
            failure_mode=effective.failure.failure_mode,
        )
    mutation_api = FakeLambdaMutationAPI()
    journal.append("fake_launch_requested", idempotency_key=idempotency_key)
    for index, node in enumerate(launch_plan.nodes):
        requested_id = make_fake_resource_id("instance", lifecycle_id=lifecycle_id, index=index)
        mutation_response = mutation_api.fake_launch_instance(
            FakeLambdaLaunchRequest(
                lifecycle_id=lifecycle_id,
                resource_index=index,
                instance_type=launch_plan.instance_type,
                region=launch_plan.region,
                requested_instance_id=requested_id,
                idempotency_key=f"{idempotency_key}:launch:{index}",
            )
        )
        resource_id = mutation_response.instance_id
        journal.append(
            "fake_launch_started",
            resource_id=resource_id,
            idempotency_key=idempotency_key,
            payload={
                "launch_plan_node_id": node.node_id,
                "fake_mutation_api": mutation_response.model_dump(mode="json"),
            },
        )
        journal.append(
            "fake_instance_running",
            resource_id=resource_id,
            idempotency_key=idempotency_key,
        )
        failed_before_health = effective.failure.enabled(
            "fail_after_launch_before_health"
        ) or effective.failure.enabled("process_crash_after_fake_launch")
        if failed_before_health:
            continue
        mode = "timeout" if effective.failure.enabled("health_check_timeout") else "pass"
        health = run_fake_lambda_health_check(resource_id, mode=mode)
        journal.append(
            "fake_health_check_passed" if health.healthy else "fake_health_check_failed",
            resource_id=resource_id,
            idempotency_key=idempotency_key,
            payload=health.model_dump(mode="json"),
        )
    replay = journal.replay()
    errors: list[str] = []
    warnings: list[str] = []
    if effective.failure.failure_mode != "none":
        warnings.append(f"injected failure mode: {effective.failure.failure_mode}")
    return _report_from_state(
        m020=m020,
        m020_report_path=m020_report_path,
        approval_manifest_path=approval_manifest_path,
        lifecycle_id=lifecycle_id,
        journal_path=journal_path,
        state=replay.state,
        idempotency_key=idempotency_key,
        errors=errors,
        warnings=warnings,
        failure_mode=effective.failure.failure_mode,
    )


def _report_from_state(
    *,
    m020,
    m020_report_path: str | Path,
    approval_manifest_path: str | Path,
    lifecycle_id: str,
    journal_path: Path,
    state,
    idempotency_key: str,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    failure_mode: str = "none",
) -> FakeLambdaLifecycleReport:
    errors = errors or []
    warnings = warnings or []
    created = len(state.resources)
    healthy = sum(1 for record in state.resources.values() if record.state == "healthy")
    terminated = sum(1 for record in state.resources.values() if record.state == "terminated")
    manual_review = any(
        record.state in {"running", "unhealthy", "failed_launch", "orphan_candidate"}
        for record in state.resources.values()
    )
    passed = bool(created) and healthy == created and not errors
    return FakeLambdaLifecycleReport(
        run_id=m020.price_reconciliation.shape_match.requested_instance_type or "lambda-fake",
        fake_lifecycle_id=lifecycle_id,
        fake_mutating_operations=created,
        launch_plan_ref=m020.launch_plan_ref,
        teardown_plan_ref=m020.teardown_plan_ref,
        m020_report_ref=str(m020_report_path),
        approval_manifest_ref=str(approval_manifest_path),
        lifecycle_journal_ref=str(journal_path),
        lifecycle_state=state,
        fake_resources_created=created,
        fake_resources_terminated=terminated,
        unmanaged_live_resources_detected=m020.resource_reconciliation.unmanaged_billable_instances,
        health_check_summary={"healthy": healthy, "resource_count": created},
        idempotency_summary={"idempotency_key": idempotency_key},
        failure_injection_summary={"failure_mode": failure_mode},
        manual_review_required=manual_review,
        fake_lifecycle_passed=passed,
        warnings=warnings,
        errors=errors,
    )


def _lifecycle_id(idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:12]
    return f"fake-life-{digest}"
