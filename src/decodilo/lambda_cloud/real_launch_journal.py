"""Append-only M029 launch journal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

LambdaM029JournalEventType = Literal[
    "m029_preflight_started",
    "m029_arming_succeeded",
    "m029_launch_request_about_to_send",
    "m029_launch_request_sent",
    "m029_launch_response_received",
    "m029_launch_response_timeout",
    "m029_owned_instance_recorded",
    "m029_readonly_verify_running",
    "m029_termination_request_about_to_send",
    "m029_termination_request_sent",
    "m029_termination_response_received",
    "m029_termination_response_timeout",
    "m029_readonly_verify_terminated",
    "m029_manual_review_required",
    "m029_run_completed",
]


class LambdaM029JournalEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_schema_version: int = 1
    event_id: str
    run_id: str
    event_type: LambdaM029JournalEventType
    sequence: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True)


class LambdaM029JournalReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    replay_passed: bool
    events_seen: int
    owned_instance_id: str | None = None
    termination_verified: bool = False
    corrupted: bool = False
    errors: list[str] = Field(default_factory=list)


class LambdaM029LaunchJournal:
    def __init__(self, path: str | Path, *, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: LambdaM029JournalEventType,
        *,
        metadata: dict[str, Any] | None = None,
        real_lambda_api_used: bool = False,
        billable_action_performed: bool = False,
    ) -> LambdaM029JournalEvent:
        sequence = _next_sequence(self.path)
        event = LambdaM029JournalEvent(
            event_id=_event_id(self.run_id, event_type, sequence),
            run_id=self.run_id,
            event_type=event_type,
            sequence=sequence,
            metadata=metadata or {},
            real_lambda_api_used=real_lambda_api_used,
            billable_action_performed=billable_action_performed,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.to_json() + "\n")
        return event


def replay_m029_launch_journal(path: str | Path) -> LambdaM029JournalReplayResult:
    journal = Path(path)
    owned: str | None = None
    terminated = False
    count = 0
    errors: list[str] = []
    try:
        for raw in journal.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            count += 1
            event = LambdaM029JournalEvent.model_validate_json(raw)
            if event.event_type == "m029_owned_instance_recorded":
                owned = str(event.metadata.get("owned_instance_id") or "")
            if event.event_type == "m029_readonly_verify_terminated":
                terminated = bool(event.metadata.get("termination_verified"))
    except Exception as exc:  # noqa: BLE001 - journal corruption is reported
        errors.append(str(exc))
        return LambdaM029JournalReplayResult(
            replay_passed=False,
            events_seen=count,
            corrupted=True,
            errors=errors,
        )
    return LambdaM029JournalReplayResult(
        replay_passed=True,
        events_seen=count,
        owned_instance_id=owned,
        termination_verified=terminated,
    )


def _next_sequence(path: Path) -> int:
    if not path.exists():
        return 1
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) + 1


def _event_id(run_id: str, event_type: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{run_id}:{event_type}:{sequence}".encode()).hexdigest()
    return f"m029-event-{digest[:16]}"
