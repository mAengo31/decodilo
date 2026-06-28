"""Bounded local synthetic learner/syncer smoke command."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.runtime.update_stream import UpdateStream
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.replay import replay_events
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge

LearnerSyncerSmokeStatus = Literal["passed", "failed"]


class LearnerSyncerSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_syncer_smoke_status: LearnerSyncerSmokeStatus
    command: str = "dev learner-syncer-smoke"
    synthetic: bool
    max_steps: int
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    real_model_training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    learner_check_passed: bool | None = None
    syncer_check_passed: bool | None = None
    learner_syncer_exchange_check_passed: bool | None = None
    update_or_commit_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    artifact_or_report_check_passed: bool | None = None
    synthetic_steps_requested: int
    synthetic_steps_completed: int = 0
    synthetic_updates_produced: int = 0
    synthetic_updates_accepted: int = 0
    synthetic_updates_rejected: int = 0
    sync_rounds_completed: int = 0
    global_version_before: int | None = None
    global_version_after: int | None = None
    useful_synthetic_tokens: int | None = None
    useful_synthetic_tokens_reason: str | None = None
    stale_update_count: int | None = None
    stale_update_count_reason: str | None = None
    duplicate_update_count: int | None = None
    duplicate_update_count_reason: str | None = None
    runtime_checks: dict[str, bool | int | float | str] = Field(default_factory=dict)
    modules_imported: list[str] = Field(default_factory=list)
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
    def _validate_disabled(self) -> LearnerSyncerSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("learner/syncer smoke report cannot enable launch")
        if (
            self.network_used
            or self.package_install_attempted
            or self.download_attempted
            or self.training_attempted
            or self.real_model_training_attempted
            or self.torch_required
            or self.gpu_required
            or self.background_process_started
        ):
            raise ValueError("learner/syncer smoke report cannot require unsafe behavior")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_learner_syncer_smoke(
    *,
    synthetic: bool,
    max_steps: int,
    out: str | Path,
) -> LearnerSyncerSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    runtime_checks: dict[str, bool | int | float | str] = {}
    metrics: dict[str, bool | int | float | str] = {}
    if not synthetic:
        errors.append("learner/syncer smoke requires --synthetic")
    if max_steps != 1:
        errors.append("learner/syncer smoke currently requires --max-steps 1")
    if not errors:
        try:
            metrics = _run_one_step_learner_syncer_exchange()
            runtime_checks.update(metrics)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"learner_syncer_exchange_failed:{type(exc).__name__}")
    learner_passed = bool(metrics.get("learner_update_constructed", False))
    syncer_passed = bool(metrics.get("syncer_merge_committed", False))
    exchange_passed = bool(metrics.get("learner_syncer_exchange_completed", False))
    update_passed = bool(metrics.get("update_ack_observed", False))
    replay_passed = bool(metrics.get("replay_validated", False))
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = LearnerSyncerSmokeReport(
        learner_syncer_smoke_status=(
            "passed"
            if (
                not errors
                and learner_passed
                and syncer_passed
                and exchange_passed
                and update_passed
                and replay_passed
            )
            else "failed"
        ),
        synthetic=synthetic,
        max_steps=max_steps,
        learner_check_passed=learner_passed,
        syncer_check_passed=syncer_passed,
        learner_syncer_exchange_check_passed=exchange_passed,
        update_or_commit_check_passed=update_passed,
        replay_or_metric_check_passed=replay_passed,
        artifact_or_report_check_passed=False,
        synthetic_steps_requested=max_steps,
        synthetic_steps_completed=int(metrics.get("synthetic_steps_completed", 0)),
        synthetic_updates_produced=int(metrics.get("synthetic_updates_produced", 0)),
        synthetic_updates_accepted=int(metrics.get("synthetic_updates_accepted", 0)),
        synthetic_updates_rejected=int(metrics.get("synthetic_updates_rejected", 0)),
        sync_rounds_completed=int(metrics.get("sync_rounds_completed", 0)),
        global_version_before=(
            int(metrics["global_version_before"])
            if "global_version_before" in metrics
            else None
        ),
        global_version_after=(
            int(metrics["global_version_after"])
            if "global_version_after" in metrics
            else None
        ),
        useful_synthetic_tokens=(
            int(metrics["useful_synthetic_tokens"])
            if "useful_synthetic_tokens" in metrics
            else None
        ),
        useful_synthetic_tokens_reason=None
        if "useful_synthetic_tokens" in metrics
        else "not meaningful because exchange did not complete",
        stale_update_count=(
            int(metrics["stale_update_count"]) if "stale_update_count" in metrics else None
        ),
        stale_update_count_reason=None
        if "stale_update_count" in metrics
        else "not meaningful because exchange did not complete",
        duplicate_update_count=(
            int(metrics["duplicate_update_count"])
            if "duplicate_update_count" in metrics
            else None
        ),
        duplicate_update_count_reason=None
        if "duplicate_update_count" in metrics
        else "not meaningful because exchange did not complete",
        runtime_checks=runtime_checks,
        modules_imported=[
            "decodilo.runtime.update_stream",
            "decodilo.syncer.event_log",
            "decodilo.syncer.replay",
            "decodilo.syncer.token_weighted_merge",
        ],
        skipped_checks={
            "real_training": "forbidden for learner/syncer smoke",
            "network": "forbidden for learner/syncer smoke",
            "gpu": "not required for learner/syncer smoke",
            "torch": "not required for learner/syncer smoke",
            "subprocess_or_service_syncer": (
                "skipped; deterministic in-memory protocol primitives are used"
            ),
        },
        failed_check=failed_check,
        error_classification=error_classification,
        safe_error_message=safe_error_message,
        elapsed_seconds=max(0.0, time.monotonic() - start),
        errors=errors,
    )
    report = _with_stable_artifact_size(report)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
    loaded = load_learner_syncer_smoke_report(target)
    artifact_report_passed = (
        loaded.learner_syncer_smoke_status == report.learner_syncer_smoke_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 20_000
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_learner_syncer_smoke_report(path: str | Path) -> LearnerSyncerSmokeReport:
    return LearnerSyncerSmokeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_one_step_learner_syncer_exchange() -> dict[str, bool | int | float | str]:
    learner_id = "learner-0"
    global_version_before = 0
    global_version_after = 1
    tokens = 13
    base_vector = np.asarray([0.0, 0.0, 0.0], dtype=np.float64)
    learner_vector = np.asarray([0.25, -0.5, 0.75], dtype=np.float64)
    merge = token_weighted_merge(
        base_vector,
        [
            LearnerDelta(
                learner_id=learner_id,
                vector=learner_vector,
                tokens=tokens,
                global_version_seen=global_version_before,
            )
        ],
        optimizer=SGDOuterOptimizer(outer_lr=1.0),
    )

    async def update_delivery() -> dict[str, bool | int | float | str]:
        stream = UpdateStream(max_version_lag=1)
        stream.register(learner_id, version=global_version_before)
        pending_update = asyncio.create_task(
            stream.wait_for_update(
                learner_id=learner_id,
                learner_version=global_version_before,
                current_version=global_version_before,
                timeout_seconds=1.0,
            )
        )
        await asyncio.sleep(0)
        pre_commit_wait_pending = not pending_update.done()
        stream.notify_commit(global_version=global_version_after)
        update_ready = await asyncio.wait_for(pending_update, timeout=1.0)
        stream.mark_sent(learner_id, global_version=global_version_after)
        stream.ack(
            learner_id,
            global_version=global_version_after,
            current_version=global_version_after,
        )
        stream.ack(
            learner_id,
            global_version=global_version_after,
            current_version=global_version_after,
        )
        stale = stream.stale_learners(current_version=global_version_after)
        metrics = stream.metrics_dict()
        return {
            "update_stream_pre_commit_wait_pending": pre_commit_wait_pending,
            "update_ready_after_commit": update_ready is True,
            "global_update_broadcasts": int(metrics["global_update_broadcasts"]),
            "global_update_messages_sent": int(metrics["global_update_messages_sent"]),
            "global_update_acks": int(metrics["global_update_acks"]),
            "duplicate_update_count": int(metrics["duplicate_global_update_acks"]),
            "stale_update_count": len(stale),
            "learner_lag_zero": stream.learner_update_lag_current == {learner_id: 0},
        }

    update_metrics = asyncio.run(update_delivery())
    log = EventLog(path=None, run_id="learner-syncer-smoke")
    log.append(
        EventType.LEARNER_STARTED,
        logical_time=0,
        learner_id=learner_id,
        payload={"learner_id": learner_id, "global_version_seen": global_version_before},
    )
    log.append(
        EventType.LEARNER_FRAGMENT_SUBMITTED,
        logical_time=1,
        learner_id=learner_id,
        payload={
            "learner_id": learner_id,
            "global_version_seen": global_version_before,
            "tokens": tokens,
            "vector": learner_vector.tolist(),
        },
    )
    log.append(
        EventType.SYNC_ROUND_STARTED,
        logical_time=2,
        round_id="round-0",
        payload={
            "round_id": "round-0",
            "previous_global_version": global_version_before,
            "accepted_learner_ids": [learner_id],
        },
    )
    log.append(
        EventType.SYNC_ROUND_COMMITTED,
        logical_time=3,
        round_id="round-0",
        payload={
            "round_id": "round-0",
            "previous_global_version": global_version_before,
            "new_global_version": global_version_after,
            "accepted_learner_ids": [learner_id],
            "useful_tokens": tokens,
            "outer_lr": 1.0,
            "old_global_vector": base_vector.tolist(),
            "weighted_delta": merge.weighted_delta.tolist(),
            "new_global_vector": merge.new_global_vector.tolist(),
        },
    )
    log.append(
        EventType.GLOBAL_UPDATE_SENT,
        logical_time=4,
        learner_id=learner_id,
        payload={"learner_id": learner_id, "global_version": global_version_after},
    )
    log.append(
        EventType.GLOBAL_UPDATE_ACKED,
        logical_time=5,
        learner_id=learner_id,
        payload={"learner_id": learner_id, "global_version": global_version_after},
    )
    replay = replay_events(log.events)
    if replay.final_global_vector is None:
        raise AssertionError("learner/syncer replay did not produce final vector")
    if not np.allclose(replay.final_global_vector, merge.new_global_vector):
        raise AssertionError("learner/syncer replay final vector mismatch")
    return {
        **update_metrics,
        "learner_update_constructed": True,
        "syncer_merge_committed": replay.sync_rounds_committed == 1,
        "learner_syncer_exchange_completed": replay.accepted_useful_tokens == tokens,
        "update_ack_observed": update_metrics["global_update_acks"] == 1,
        "replay_validated": replay.accepted_useful_tokens == tokens,
        "synthetic_steps_completed": 1,
        "synthetic_updates_produced": 1,
        "synthetic_updates_accepted": 1,
        "synthetic_updates_rejected": replay.rejected_update_count,
        "sync_rounds_completed": replay.sync_rounds_committed,
        "global_version_before": global_version_before,
        "global_version_after": global_version_after,
        "useful_synthetic_tokens": replay.accepted_useful_tokens,
        "event_log_event_count": len(log.events),
        "final_global_vector_l2": float(np.linalg.norm(replay.final_global_vector)),
        "token_weight_learner_0": float(merge.token_weights[learner_id]),
    }


def _with_stable_artifact_size(
    report: LearnerSyncerSmokeReport,
) -> LearnerSyncerSmokeReport:
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
    if first.startswith("learner/syncer smoke requires --synthetic"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("learner/syncer smoke currently requires --max-steps"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("learner_syncer_exchange_failed:"):
        return (
            "learner_syncer_exchange_check",
            "learner_syncer_exchange_failed",
            first,
        )
    return "learner_syncer_smoke", "learner_syncer_smoke_failed", first
