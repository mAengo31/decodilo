"""Fake Lambda teardown executor for synthetic resources only."""

from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.fake_lifecycle_failures import FakeLambdaFailureConfig
from decodilo.lambda_cloud.fake_lifecycle_journal import FakeLambdaLifecycleJournal
from decodilo.lambda_cloud.fake_lifecycle_report import (
    FakeLambdaLifecycleReport,
    load_fake_lambda_lifecycle_report,
)
from decodilo.lambda_cloud.fake_mutation_api import FakeLambdaMutationAPI
from decodilo.lambda_cloud.fake_mutation_models import FakeLambdaTerminateRequest


def execute_fake_lambda_teardown(
    *,
    lifecycle_report_path: str | Path,
    failure: FakeLambdaFailureConfig | None = None,
) -> FakeLambdaLifecycleReport:
    original = load_fake_lambda_lifecycle_report(lifecycle_report_path)
    effective = failure or FakeLambdaFailureConfig()
    journal = FakeLambdaLifecycleJournal(
        original.lifecycle_journal_ref,
        lifecycle_id=original.fake_lifecycle_id,
    )
    state = journal.replay().state
    mutation_api = FakeLambdaMutationAPI()
    journal.append("fake_teardown_requested")
    for index, record in enumerate(state.resources.values()):
        if record.state == "terminated":
            continue
        mutation_response = mutation_api.fake_terminate_instance(
            FakeLambdaTerminateRequest(
                instance_id=record.resource_id,
                idempotency_key=f"{original.fake_lifecycle_id}:terminate:{index}",
            )
        )
        journal.append("fake_terminate_started", resource_id=record.resource_id)
        if (
            effective.enabled("partial_terminate_failure")
            and index == effective.fail_resource_index
        ):
            journal.append("fake_terminate_failed", resource_id=record.resource_id)
            continue
        if effective.enabled("terminate_timeout"):
            journal.append("fake_terminate_failed", resource_id=record.resource_id)
            continue
        journal.append(
            "fake_instance_terminated",
            resource_id=record.resource_id,
            payload={"fake_mutation_api": mutation_response.model_dump(mode="json")},
        )
    replay = journal.replay()
    terminated = sum(1 for item in replay.state.resources.values() if item.state == "terminated")
    remaining = len(replay.state.resources) - terminated
    return original.model_copy(
        update={
            "lifecycle_state": replay.state,
            "fake_resources_terminated": terminated,
            "fake_mutating_operations": original.fake_mutating_operations + terminated,
            "teardown_verification": {
                "terminated": terminated,
                "remaining": remaining,
                "passed": remaining == 0,
            },
            "manual_review_required": remaining > 0,
            "fake_lifecycle_passed": remaining == 0 and not original.errors,
            "failure_injection_summary": {
                **original.failure_injection_summary,
                "teardown_failure_mode": effective.failure_mode,
            },
            "warnings": [
                *original.warnings,
                *(["fake teardown left resources requiring manual review"] if remaining else []),
            ],
        }
    )
