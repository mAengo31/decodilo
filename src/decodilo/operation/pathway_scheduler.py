"""Small Pathway-style scheduler primitives for production-shaped DiLoCo plans.

This is intentionally not Google Pathways. It provides the minimal semantics the
repo needs before scaling further: explicit DAG tasks, artifact futures,
retry/resume accounting, resource policy checks, and fail-closed launch flags.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


class PathwaySchedulerError(RuntimeError):
    """Raised when a Pathway-style plan cannot be scheduled or executed."""


@dataclass(frozen=True)
class PathwayArtifactFuture:
    """Resolved artifact future produced by a scheduler task."""

    artifact_id: str
    producer_task_id: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "producer_task_id": self.producer_task_id,
            "value": _json_safe(self.value),
        }


@dataclass(frozen=True)
class PathwayResourcePolicy:
    """Fail-closed resource policy for scheduler execution."""

    local_only: bool = True
    allow_remote: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    production_scale_ready: bool = False

    def validate_task(self, task: PathwayTask) -> None:
        if task.remote and (self.local_only or not self.allow_remote):
            raise PathwaySchedulerError(f"remote task blocked: {task.task_id}")
        if task.remote and (not self.launch_ready or not self.launch_allowed):
            raise PathwaySchedulerError(f"remote launch not allowed: {task.task_id}")


@dataclass(frozen=True)
class PathwayTask:
    """One scheduler task with explicit artifact dependencies."""

    task_id: str
    op: str
    run: Callable[[PathwayExecutionContext], Mapping[str, Any] | None]
    depends_on: list[str] = field(default_factory=list)
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    max_attempts: int = 1
    remote: bool = False
    resource_tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id is required")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


@dataclass(frozen=True)
class PathwayScheduleResult:
    status: str
    execution_order: list[str]
    task_attempts: dict[str, int]
    artifacts: dict[str, PathwayArtifactFuture]
    launch_ready: bool = False
    launch_allowed: bool = False
    production_scale_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "execution_order": list(self.execution_order),
            "task_attempts": dict(self.task_attempts),
            "artifacts": {
                key: future.to_dict() for key, future in self.artifacts.items()
            },
            "launch_ready": self.launch_ready,
            "launch_allowed": self.launch_allowed,
            "production_scale_ready": self.production_scale_ready,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class PathwayExecutionContext:
    """Read-only task context over resolved artifact futures."""

    def __init__(self, artifacts: Mapping[str, PathwayArtifactFuture]) -> None:
        self._artifacts = artifacts

    def resolve(self, artifact_id: str) -> Any:
        if artifact_id not in self._artifacts:
            raise PathwaySchedulerError(f"missing artifact: {artifact_id}")
        return self._artifacts[artifact_id].value

    def future(self, artifact_id: str) -> PathwayArtifactFuture:
        if artifact_id not in self._artifacts:
            raise PathwaySchedulerError(f"missing artifact: {artifact_id}")
        return self._artifacts[artifact_id]


class PathwayScheduler:
    """Deterministic DAG scheduler with artifact futures and retries."""

    def __init__(self, *, resource_policy: PathwayResourcePolicy | None = None) -> None:
        self.resource_policy = resource_policy or PathwayResourcePolicy()
        self._tasks: dict[str, PathwayTask] = {}

    def add_task(self, task: PathwayTask) -> None:
        if task.task_id in self._tasks:
            raise PathwaySchedulerError(f"duplicate task_id: {task.task_id}")
        self._tasks[task.task_id] = task

    def run(self) -> PathwayScheduleResult:
        order = self._topological_order()
        artifacts: dict[str, PathwayArtifactFuture] = {}
        attempts: dict[str, int] = {}
        completed: list[str] = []
        for task_id in order:
            task = self._tasks[task_id]
            self.resource_policy.validate_task(task)
            for artifact_id in task.consumes:
                if artifact_id not in artifacts:
                    raise PathwaySchedulerError(
                        f"task {task.task_id} missing artifact: {artifact_id}"
                    )
            last_error: BaseException | None = None
            for attempt in range(1, task.max_attempts + 1):
                attempts[task.task_id] = attempt
                try:
                    output = dict(task.run(PathwayExecutionContext(artifacts)) or {})
                    break
                except Exception as exc:  # noqa: BLE001 - task-specific transient failures
                    last_error = exc
                    if attempt == task.max_attempts:
                        raise PathwaySchedulerError(
                            f"task {task.task_id} failed after {attempt} attempts: {exc}"
                        ) from exc
            else:  # pragma: no cover - defensive; loop always breaks or raises
                raise PathwaySchedulerError(f"task {task.task_id} failed: {last_error}")
            for artifact_id in task.produces:
                if artifact_id not in output:
                    raise PathwaySchedulerError(
                        f"task {task.task_id} did not produce artifact: {artifact_id}"
                    )
                artifacts[artifact_id] = PathwayArtifactFuture(
                    artifact_id=artifact_id,
                    producer_task_id=task.task_id,
                    value=output[artifact_id],
                )
            completed.append(task.task_id)
        return PathwayScheduleResult(
            status="completed",
            execution_order=completed,
            task_attempts=attempts,
            artifacts=artifacts,
            launch_ready=False,
            launch_allowed=False,
            production_scale_ready=False,
        )

    def _topological_order(self) -> list[str]:
        for task in self._tasks.values():
            for dependency in task.depends_on:
                if dependency not in self._tasks:
                    raise PathwaySchedulerError(
                        f"missing dependency {dependency!r} for task {task.task_id!r}"
                    )
        temporary: set[str] = set()
        permanent: set[str] = set()
        order: list[str] = []

        def visit(task_id: str) -> None:
            if task_id in permanent:
                return
            if task_id in temporary:
                raise PathwaySchedulerError("cycle detected in pathway task graph")
            temporary.add(task_id)
            for dependency in self._tasks[task_id].depends_on:
                visit(dependency)
            temporary.remove(task_id)
            permanent.add(task_id)
            order.append(task_id)

        for task_id in list(self._tasks):
            visit(task_id)
        return order


def _json_safe(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
