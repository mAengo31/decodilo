"""Bounded local synthetic Decodilo runtime experiment command."""

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

SyntheticExperimentStatus = Literal["passed", "failed"]


class SyntheticExperimentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    synthetic_experiment_status: SyntheticExperimentStatus
    command: str = "dev synthetic-experiment"
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
    learner_or_runtime_check_passed: bool | None = None
    update_or_commit_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    artifact_or_report_check_passed: bool | None = None
    useful_synthetic_steps: int = 0
    synthetic_updates_produced: int = 0
    synthetic_updates_accepted: int = 0
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
    def _validate_disabled(self) -> SyntheticExperimentReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("synthetic experiment report cannot enable launch")
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
            raise ValueError("synthetic experiment report cannot require unsafe behavior")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_synthetic_experiment(
    *,
    synthetic: bool,
    max_steps: int,
    out: str | Path,
) -> SyntheticExperimentReport:
    start = time.monotonic()
    errors: list[str] = []
    runtime_checks: dict[str, bool | int | float | str] = {}
    learner_or_runtime_passed = False
    update_or_commit_passed = False
    replay_or_metric_passed = False
    artifact_report_passed = False
    useful_steps = 0
    updates_produced = 0
    updates_accepted = 0
    if not synthetic:
        errors.append("synthetic experiment requires --synthetic")
    if max_steps != 1:
        errors.append("synthetic experiment currently requires --max-steps 1")
    if not errors:
        try:
            metrics = _run_one_step_synthetic_protocol_experiment()
            runtime_checks.update(metrics)
            learner_or_runtime_passed = bool(metrics["learner_fragment_submitted"])
            update_or_commit_passed = bool(metrics["sync_round_committed"])
            replay_or_metric_passed = bool(metrics["replay_validated"])
            useful_steps = int(metrics["sync_rounds_committed"])
            updates_produced = int(metrics["synthetic_updates_produced"])
            updates_accepted = int(metrics["synthetic_updates_accepted"])
        except Exception as exc:  # noqa: BLE001
            errors.append(f"synthetic_protocol_experiment_failed:{type(exc).__name__}")
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = SyntheticExperimentReport(
        synthetic_experiment_status=(
            "passed"
            if (
                not errors
                and learner_or_runtime_passed
                and update_or_commit_passed
                and replay_or_metric_passed
            )
            else "failed"
        ),
        synthetic=synthetic,
        max_steps=max_steps,
        learner_or_runtime_check_passed=learner_or_runtime_passed,
        update_or_commit_check_passed=update_or_commit_passed,
        replay_or_metric_check_passed=replay_or_metric_passed,
        artifact_or_report_check_passed=artifact_report_passed,
        useful_synthetic_steps=useful_steps,
        synthetic_updates_produced=updates_produced,
        synthetic_updates_accepted=updates_accepted,
        runtime_checks=runtime_checks,
        modules_imported=[
            "decodilo.runtime.update_stream",
            "decodilo.syncer.event_log",
            "decodilo.syncer.replay",
            "decodilo.syncer.token_weighted_merge",
        ],
        skipped_checks={
            "real_training": "forbidden for synthetic experiment",
            "network": "forbidden for synthetic experiment",
            "gpu": "not required for synthetic experiment",
            "torch": "not required for synthetic experiment",
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
    loaded = load_synthetic_experiment_report(target)
    artifact_report_passed = (
        loaded.synthetic_experiment_status == report.synthetic_experiment_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 16384
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_synthetic_experiment_report(path: str | Path) -> SyntheticExperimentReport:
    return SyntheticExperimentReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_one_step_synthetic_protocol_experiment() -> dict[str, bool | int | float | str]:
    async def update_delivery_scenario() -> dict[str, bool | int | float | str]:
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
        stream.mark_sent("learner-0", global_version=1)
        stream.ack("learner-0", global_version=1, current_version=1)
        metrics = stream.metrics_dict()
        return {
            "update_stream_pre_commit_wait_pending": pre_commit_wait_pending,
            "update_stream_ready_after_commit": update_ready is True,
            "global_update_broadcasts": int(metrics["global_update_broadcasts"]),
            "global_update_messages_sent": int(metrics["global_update_messages_sent"]),
            "global_update_acks": int(metrics["global_update_acks"]),
            "learner_lag_zero": stream.learner_update_lag_current == {"learner-0": 0},
        }

    update_metrics = asyncio.run(update_delivery_scenario())
    initial_vector = np.asarray([0.0, 0.0], dtype=np.float64)
    learner_vector = np.asarray([0.5, -0.25], dtype=np.float64)
    tokens = 8
    outer_lr = 1.0
    merge = token_weighted_merge(
        initial_vector,
        [
            LearnerDelta(
                learner_id="learner-0",
                vector=learner_vector,
                tokens=tokens,
                global_version_seen=0,
            )
        ],
        optimizer=SGDOuterOptimizer(outer_lr=outer_lr),
    )
    log = EventLog(path=None, run_id="synthetic-experiment")
    log.append(
        EventType.LEARNER_FRAGMENT_SUBMITTED,
        logical_time=0,
        learner_id="learner-0",
        payload={
            "learner_id": "learner-0",
            "global_version_seen": 0,
            "tokens": tokens,
            "vector": learner_vector.tolist(),
        },
    )
    log.append(
        EventType.SYNC_ROUND_STARTED,
        logical_time=1,
        round_id="round-0",
        payload={
            "round_id": "round-0",
            "previous_global_version": 0,
            "accepted_learner_ids": ["learner-0"],
        },
    )
    log.append(
        EventType.SYNC_ROUND_COMMITTED,
        logical_time=2,
        round_id="round-0",
        payload={
            "round_id": "round-0",
            "previous_global_version": 0,
            "new_global_version": 1,
            "accepted_learner_ids": ["learner-0"],
            "useful_tokens": tokens,
            "outer_lr": outer_lr,
            "old_global_vector": initial_vector.tolist(),
            "weighted_delta": merge.weighted_delta.tolist(),
            "new_global_vector": merge.new_global_vector.tolist(),
        },
    )
    log.append(
        EventType.GLOBAL_UPDATE_SENT,
        logical_time=3,
        learner_id="learner-0",
        payload={"learner_id": "learner-0", "global_version": 1},
    )
    log.append(
        EventType.GLOBAL_UPDATE_ACKED,
        logical_time=4,
        learner_id="learner-0",
        payload={"learner_id": "learner-0", "global_version": 1},
    )
    replay = replay_events(log.events)
    if replay.final_global_vector is None:
        raise AssertionError("synthetic replay did not produce a final vector")
    if not np.allclose(replay.final_global_vector, merge.new_global_vector):
        raise AssertionError("synthetic replay final vector mismatch")
    return {
        **update_metrics,
        "learner_fragment_submitted": True,
        "sync_round_committed": replay.sync_rounds_committed == 1,
        "replay_validated": replay.accepted_useful_tokens == tokens,
        "event_log_event_count": len(log.events),
        "sync_rounds_committed": replay.sync_rounds_committed,
        "accepted_useful_tokens": replay.accepted_useful_tokens,
        "synthetic_updates_produced": int(merge.useful_tokens > 0),
        "synthetic_updates_accepted": int(replay.accepted_useful_tokens > 0),
        "final_global_vector_l2": float(np.linalg.norm(replay.final_global_vector)),
        "token_weight_learner_0": float(merge.token_weights["learner-0"]),
    }


def _with_stable_artifact_size(
    report: SyntheticExperimentReport,
) -> SyntheticExperimentReport:
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
    if first.startswith("synthetic experiment requires --synthetic"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("synthetic experiment currently requires --max-steps"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("synthetic_protocol_experiment_failed:"):
        return (
            "synthetic_runtime_protocol_step",
            "synthetic_protocol_experiment_failed",
            first,
        )
    return "synthetic_experiment", "synthetic_experiment_failed", first
