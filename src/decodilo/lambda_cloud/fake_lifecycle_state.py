"""Fake Lambda lifecycle state machine with synthetic resource IDs only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FakeLambdaResourceType = Literal["instance", "ssh_key", "filesystem", "placement_group"]
FakeLambdaResourceState = Literal[
    "planned",
    "launch_requested",
    "launching",
    "running",
    "healthy",
    "unhealthy",
    "terminate_requested",
    "terminating",
    "terminated",
    "failed_launch",
    "failed_terminate",
    "orphan_candidate",
    "unknown",
]

_PREFIX_BY_TYPE = {
    "instance": "fake-i-",
    "ssh_key": "fake-key-",
    "filesystem": "fake-fs-",
    "placement_group": "fake-pg-",
}
_ALLOWED_TRANSITIONS: dict[FakeLambdaResourceState, set[FakeLambdaResourceState]] = {
    "planned": {"launch_requested", "failed_launch"},
    "launch_requested": {"launching", "failed_launch"},
    "launching": {"running", "failed_launch"},
    "running": {"healthy", "unhealthy", "terminate_requested", "orphan_candidate"},
    "healthy": {"unhealthy", "terminate_requested", "orphan_candidate"},
    "unhealthy": {"terminate_requested", "failed_launch", "orphan_candidate"},
    "terminate_requested": {"terminating", "failed_terminate", "terminated"},
    "terminating": {"terminated", "failed_terminate"},
    "failed_terminate": {"terminate_requested", "orphan_candidate"},
    "failed_launch": {"terminate_requested", "orphan_candidate"},
    "orphan_candidate": {"terminate_requested", "terminated"},
    "terminated": {"terminated"},
    "unknown": {"planned", "orphan_candidate"},
}


class FakeLambdaResourceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_id: str
    resource_type: FakeLambdaResourceType
    state: FakeLambdaResourceState
    idempotency_key: str | None = None
    launch_plan_node_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_synthetic_id(self) -> FakeLambdaResourceRecord:
        expected_prefix = _PREFIX_BY_TYPE[self.resource_type]
        if not self.resource_id.startswith(expected_prefix):
            raise ValueError(
                f"fake {self.resource_type} id must start with {expected_prefix!r}"
            )
        return self


class FakeLambdaLifecycleTransition(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_id: str
    from_state: FakeLambdaResourceState
    to_state: FakeLambdaResourceState
    reason: str = ""


class FakeLambdaLifecycleState(BaseModel):
    model_config = ConfigDict(frozen=True)

    lifecycle_id: str
    resources: dict[str, FakeLambdaResourceRecord] = Field(default_factory=dict)
    fake_only: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False

    def add_resource(self, record: FakeLambdaResourceRecord) -> FakeLambdaLifecycleState:
        if record.resource_id in self.resources:
            existing = self.resources[record.resource_id]
            if existing.idempotency_key == record.idempotency_key:
                return self
            raise ValueError(f"fake resource already exists: {record.resource_id}")
        return self.model_copy(
            update={"resources": {**self.resources, record.resource_id: record}}
        )

    def transition(
        self,
        resource_id: str,
        to_state: FakeLambdaResourceState,
        *,
        reason: str = "",
    ) -> tuple[FakeLambdaLifecycleState, FakeLambdaLifecycleTransition]:
        if resource_id not in self.resources:
            raise ValueError(f"unknown fake resource: {resource_id}")
        record = self.resources[resource_id]
        if to_state not in _ALLOWED_TRANSITIONS[record.state]:
            raise ValueError(f"invalid fake transition: {record.state} -> {to_state}")
        updated = record.model_copy(update={"state": to_state})
        resources = {**self.resources, resource_id: updated}
        return (
            self.model_copy(update={"resources": resources}),
            FakeLambdaLifecycleTransition(
                resource_id=resource_id,
                from_state=record.state,
                to_state=to_state,
                reason=reason,
            ),
        )

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class FakeLambdaLifecycleInvariantReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    fake_only: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    resource_count: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def make_fake_resource_id(
    resource_type: FakeLambdaResourceType,
    *,
    lifecycle_id: str,
    index: int,
) -> str:
    return f"{_PREFIX_BY_TYPE[resource_type]}{lifecycle_id}-{index}"


def validate_fake_lifecycle_invariants(
    state: FakeLambdaLifecycleState,
) -> FakeLambdaLifecycleInvariantReport:
    errors: list[str] = []
    for record in state.resources.values():
        try:
            FakeLambdaResourceRecord.model_validate(record.model_dump(mode="json"))
        except ValueError as exc:
            errors.append(str(exc))
    if not state.fake_only:
        errors.append("fake lifecycle state must be fake_only=true")
    if state.real_lambda_api_used:
        errors.append("fake lifecycle state must not use real Lambda API")
    if state.billable_action_performed:
        errors.append("fake lifecycle state must not report billable action")
    return FakeLambdaLifecycleInvariantReport(
        passed=not errors,
        resource_count=len(state.resources),
        errors=errors,
    )


def load_fake_lifecycle_state(path: str | Path) -> FakeLambdaLifecycleState:
    return FakeLambdaLifecycleState.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_fake_lifecycle_state(path: str | Path, state: FakeLambdaLifecycleState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(state.to_json(), encoding="utf-8")

