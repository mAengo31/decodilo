"""Bounded local Decodilo runtime/protocol smoke command."""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.runtime.update_stream import UpdateStream
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.replay import replay_event_log

RuntimeSmokeStatus = Literal["passed", "failed"]


class RuntimeSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime_smoke_status: RuntimeSmokeStatus
    command: str = "dev runtime-smoke"
    synthetic: bool
    max_steps: int
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    runtime_checks: dict[str, bool | int | float | str] = Field(default_factory=dict)
    modules_imported: list[str] = Field(default_factory=list)
    protocol_or_event_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    artifact_or_report_check_passed: bool | None = None
    skipped_checks: dict[str, str] = Field(default_factory=dict)
    failed_check: str | None = None
    error_classification: str | None = None
    safe_error_message: str | None = None
    artifact_bytes: int = 0
    elapsed_seconds: float
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> RuntimeSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("runtime smoke report cannot enable launch")
        if (
            self.network_used
            or self.package_install_attempted
            or self.download_attempted
            or self.training_attempted
            or self.torch_required
            or self.gpu_required
            or self.background_process_started
        ):
            raise ValueError("runtime smoke report cannot require unsafe behavior")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_runtime_smoke(
    *,
    synthetic: bool,
    max_steps: int,
    out: str | Path,
) -> RuntimeSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    runtime_checks: dict[str, bool | int | float | str] = {}
    protocol_or_event_passed = False
    replay_or_metric_passed = False
    artifact_report_passed = False
    if not synthetic:
        errors.append("runtime smoke requires --synthetic")
    if max_steps != 1:
        errors.append("runtime smoke currently requires --max-steps 1")
    if not errors:
        try:
            stream_metrics = _run_update_stream_check()
            runtime_checks.update(stream_metrics)
            protocol_or_event_passed = True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"update_stream_check_failed:{type(exc).__name__}")
        try:
            replay_metrics = _run_event_replay_check()
            runtime_checks.update(replay_metrics)
            replay_or_metric_passed = True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"event_replay_check_failed:{type(exc).__name__}")
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = RuntimeSmokeReport(
        runtime_smoke_status=(
            "passed"
            if not errors and protocol_or_event_passed and replay_or_metric_passed
            else "failed"
        ),
        synthetic=synthetic,
        max_steps=max_steps,
        runtime_checks=runtime_checks,
        modules_imported=[
            "decodilo.runtime.update_stream",
            "decodilo.syncer.event_log",
            "decodilo.syncer.replay",
        ],
        protocol_or_event_check_passed=protocol_or_event_passed,
        replay_or_metric_check_passed=replay_or_metric_passed,
        artifact_or_report_check_passed=artifact_report_passed,
        failed_check=failed_check,
        error_classification=error_classification,
        safe_error_message=safe_error_message,
        skipped_checks={
            "real_training": "forbidden for runtime smoke",
            "network": "forbidden for runtime smoke",
            "gpu": "not required for runtime smoke",
            "torch": "not required for runtime smoke",
        },
        elapsed_seconds=max(0.0, time.monotonic() - start),
        errors=errors,
    )
    report = _with_stable_artifact_size(report)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
    loaded = load_runtime_smoke_report(target)
    artifact_report_passed = (
        loaded.runtime_smoke_status == report.runtime_smoke_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 8192
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_runtime_smoke_report(path: str | Path) -> RuntimeSmokeReport:
    return RuntimeSmokeReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _run_update_stream_check() -> dict[str, bool | int | float | str]:
    async def scenario() -> dict[str, bool | int | float | str]:
        stream = UpdateStream(max_version_lag=1)
        stream.register("learner-0", version=0)
        pending_update = asyncio.create_task(
            stream.wait_for_update(
                learner_id="learner-0",
                learner_version=0,
                current_version=0,
                timeout_seconds=1.0,
            )
        )
        await asyncio.sleep(0)
        pre_commit_wait_pending = not pending_update.done()
        stream.notify_commit(global_version=1)
        update_ready = await asyncio.wait_for(pending_update, timeout=1.0)
        if not pre_commit_wait_pending or not update_ready:
            raise TimeoutError("deterministic update stream did not observe commit")
        immediate_ready = await stream.wait_for_update(
            learner_id="learner-0",
            learner_version=0,
            current_version=1,
            timeout_seconds=1.0,
        )
        stream.mark_sent("learner-0", global_version=1)
        stream.ack("learner-0", global_version=1, current_version=1)
        metrics = stream.metrics_dict()
        return {
            "update_stream_pre_commit_wait_pending": pre_commit_wait_pending,
            "update_stream_ready_after_commit": update_ready is True,
            "update_stream_immediate_ready_after_commit": immediate_ready is True,
            "global_update_broadcasts": int(metrics["global_update_broadcasts"]),
            "global_update_messages_sent": int(metrics["global_update_messages_sent"]),
            "global_update_acks": int(metrics["global_update_acks"]),
            "learner_lag_zero": stream.learner_update_lag_current == {"learner-0": 0},
        }

    return asyncio.run(scenario())


def _run_event_replay_check() -> dict[str, bool | int | float | str]:
    with tempfile.TemporaryDirectory(prefix="decodilo-runtime-smoke-") as tmp:
        log_path = Path(tmp) / "events.jsonl"
        log = EventLog(log_path, run_id="runtime-smoke")
        log.append(
            EventType.GLOBAL_UPDATE_ACKED,
            logical_time=0,
            learner_id="learner-0",
            payload={"learner_id": "learner-0", "global_version": 0},
        )
        replay = replay_event_log(log_path)
        return {
            "event_log_written": log_path.exists(),
            "event_log_event_count": len(log.events),
            "event_replay_committed_rounds": replay.sync_rounds_committed,
            "event_replay_useful_tokens": replay.accepted_useful_tokens,
            "event_replay_mode": replay.replay_mode,
        }


def _with_stable_artifact_size(report: RuntimeSmokeReport) -> RuntimeSmokeReport:
    current = report
    for _ in range(8):
        size = len(current.to_json().encode("utf-8"))
        if size == current.artifact_bytes:
            return current
        current = current.model_copy(update={"artifact_bytes": size})
    return current


def _classify_failure(errors: list[str]) -> tuple[str | None, str | None, str | None]:
    if not errors:
        return None, None, None
    first = errors[0]
    if first.startswith("runtime smoke requires --synthetic"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("runtime smoke currently requires --max-steps"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("update_stream_check_failed:"):
        return "protocol_or_event_check", "update_stream_check_failed", first
    if first.startswith("event_replay_check_failed:"):
        return "replay_or_metric_check", "event_replay_check_failed", first
    return "runtime_smoke", "runtime_smoke_failed", first
