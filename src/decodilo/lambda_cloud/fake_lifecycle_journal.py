"""JSONL journal and replay for fake Lambda lifecycle rehearsal."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_lifecycle_events import FakeLambdaLifecycleEvent
from decodilo.lambda_cloud.fake_lifecycle_state import (
    FakeLambdaLifecycleState,
    FakeLambdaResourceRecord,
)


class FakeLambdaLifecycleJournalReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: FakeLambdaLifecycleState
    events_replayed: int
    passed: bool
    errors: list[str] = Field(default_factory=list)


class FakeLambdaLifecycleJournal:
    def __init__(self, path: str | Path, *, lifecycle_id: str) -> None:
        self.path = Path(path)
        self.lifecycle_id = lifecycle_id
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: str,
        *,
        resource_id: str | None = None,
        idempotency_key: str | None = None,
        payload: dict | None = None,
    ) -> FakeLambdaLifecycleEvent:
        event = FakeLambdaLifecycleEvent(
            event_id=f"fake-evt-{self._next_index():06d}",
            event_type=event_type,
            lifecycle_id=self.lifecycle_id,
            resource_id=resource_id,
            idempotency_key=idempotency_key,
            payload=payload or {},
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.stable_json() + "\n")
        return event

    def replay(self) -> FakeLambdaLifecycleJournalReplayResult:
        return replay_fake_lifecycle_journal(self.path, lifecycle_id=self.lifecycle_id)

    def _next_index(self) -> int:
        if not self.path.exists():
            return 1
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return sum(1 for line in lines if line.strip()) + 1


def replay_fake_lifecycle_journal(
    path: str | Path,
    *,
    lifecycle_id: str,
) -> FakeLambdaLifecycleJournalReplayResult:
    target = Path(path)
    state = FakeLambdaLifecycleState(lifecycle_id=lifecycle_id)
    errors: list[str] = []
    count = 0
    if not target.exists():
        return FakeLambdaLifecycleJournalReplayResult(state=state, events_replayed=0, passed=True)
    for expected_index, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = FakeLambdaLifecycleEvent.model_validate_json(line)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"corrupted fake lifecycle event: {exc}")
            break
        if event.event_id != f"fake-evt-{expected_index:06d}":
            errors.append(f"missing or out-of-order fake event at index {expected_index}")
            break
        if not event.fake_only or event.real_lambda_api_used or event.billable_action_performed:
            errors.append("fake lifecycle event violated fake-only invariants")
            break
        count += 1
        try:
            state = _apply_event(state, event)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"fake lifecycle replay failed: {exc}")
            break
    return FakeLambdaLifecycleJournalReplayResult(
        state=state,
        events_replayed=count,
        passed=not errors,
        errors=errors,
    )


def _apply_event(
    state: FakeLambdaLifecycleState,
    event: FakeLambdaLifecycleEvent,
) -> FakeLambdaLifecycleState:
    resource_id = event.resource_id
    if event.event_type == "fake_launch_requested":
        return state
    if event.event_type == "fake_launch_started" and resource_id:
        record = FakeLambdaResourceRecord(
            resource_id=resource_id,
            resource_type="instance",
            state="planned",
            idempotency_key=event.idempotency_key,
            launch_plan_node_id=str(event.payload.get("launch_plan_node_id") or ""),
        )
        state = state.add_resource(record)
        state, _ = state.transition(resource_id, "launch_requested", reason="journal replay")
        state, _ = state.transition(resource_id, "launching", reason="journal replay")
        return state
    if event.event_type == "fake_instance_running" and resource_id:
        state, _ = state.transition(resource_id, "running", reason="journal replay")
        return state
    if event.event_type == "fake_health_check_passed" and resource_id:
        state, _ = state.transition(resource_id, "healthy", reason="journal replay")
        return state
    if event.event_type == "fake_health_check_failed" and resource_id:
        state, _ = state.transition(resource_id, "unhealthy", reason="journal replay")
        return state
    if event.event_type == "fake_teardown_requested":
        return state
    if event.event_type == "fake_terminate_started" and resource_id:
        if state.resources[resource_id].state not in {"terminate_requested", "terminating"}:
            state, _ = state.transition(resource_id, "terminate_requested", reason="journal replay")
        state, _ = state.transition(resource_id, "terminating", reason="journal replay")
        return state
    if event.event_type == "fake_instance_terminated" and resource_id:
        if state.resources[resource_id].state == "terminated":
            return state
        if state.resources[resource_id].state not in {"terminating", "terminate_requested"}:
            state, _ = state.transition(resource_id, "terminate_requested", reason="journal replay")
            state, _ = state.transition(resource_id, "terminating", reason="journal replay")
        state, _ = state.transition(resource_id, "terminated", reason="journal replay")
        return state
    if event.event_type == "fake_terminate_failed" and resource_id:
        if state.resources[resource_id].state not in {"terminating", "terminate_requested"}:
            state, _ = state.transition(resource_id, "terminate_requested", reason="journal replay")
            state, _ = state.transition(resource_id, "terminating", reason="journal replay")
        state, _ = state.transition(resource_id, "failed_terminate", reason="journal replay")
        return state
    if event.event_type == "fake_orphan_detected" and resource_id:
        state, _ = state.transition(resource_id, "orphan_candidate", reason="journal replay")
    return state
