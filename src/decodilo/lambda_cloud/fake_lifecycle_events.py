"""Fake Lambda lifecycle journal event models."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FakeLambdaLifecycleEventType = Literal[
    "fake_launch_requested",
    "fake_launch_started",
    "fake_instance_running",
    "fake_health_check_passed",
    "fake_health_check_failed",
    "fake_teardown_requested",
    "fake_terminate_started",
    "fake_instance_terminated",
    "fake_terminate_failed",
    "fake_orphan_detected",
    "fake_reconcile_completed",
    "fake_budget_gate_blocked",
    "fake_approval_gate_blocked",
    "fake_lifecycle_aborted",
]


class FakeLambdaLifecycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: FakeLambdaLifecycleEventType
    lifecycle_id: str
    resource_id: str | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    fake_only: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

