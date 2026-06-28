"""Bounded local Decodilo smoke command."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.protocol import (
    CheckpointRecord,
    LearnerHeartbeat,
    LearnerStatus,
    MergeDecision,
    ModelFragment,
    QuorumDecision,
)
from decodilo.protocol.ids import make_round_id, normalize_id
from decodilo.runtime.metrics_validation import validate_report_payload
from decodilo.storage.checksums import sha256_json

TinySmokeStatus = Literal["passed", "failed"]


class TinySmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    smoke_status: TinySmokeStatus
    command: str = "dev tiny-smoke"
    synthetic: bool
    max_steps: int
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    runtime_checks: dict[str, bool | str] = Field(default_factory=dict)
    modules_imported: list[str] = Field(default_factory=list)
    protocol_or_event_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    skipped_checks: dict[str, str] = Field(default_factory=dict)
    artifact_bytes: int = 0
    elapsed_seconds: float
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> TinySmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("tiny smoke report cannot enable launch")
        if (
            self.network_used
            or self.package_install_attempted
            or self.download_attempted
            or self.training_attempted
            or self.torch_required
            or self.gpu_required
            or self.background_process_started
        ):
            raise ValueError("tiny smoke report cannot require unsafe behavior")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_tiny_smoke(
    *,
    synthetic: bool,
    max_steps: int,
    out: str | Path,
) -> TinySmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    runtime_checks: dict[str, bool | str] = {}
    protocol_passed = False
    metric_passed = False
    if not synthetic:
        errors.append("tiny smoke requires --synthetic")
    if max_steps != 1:
        errors.append("tiny smoke currently requires --max-steps 1")
    if not errors:
        try:
            protocol_passed = _run_protocol_check()
            runtime_checks["protocol_round_trip"] = protocol_passed
        except Exception as exc:  # noqa: BLE001
            errors.append(f"protocol_check_failed:{type(exc).__name__}")
        try:
            metric_passed = _run_metric_check()
            runtime_checks["metric_validation"] = metric_passed
        except Exception as exc:  # noqa: BLE001
            errors.append(f"metric_check_failed:{type(exc).__name__}")
    report = TinySmokeReport(
        smoke_status="passed" if not errors and protocol_passed and metric_passed else "failed",
        synthetic=synthetic,
        max_steps=max_steps,
        runtime_checks=runtime_checks,
        modules_imported=[
            "decodilo.protocol",
            "decodilo.protocol.ids",
            "decodilo.runtime.metrics_validation",
            "decodilo.storage.checksums",
        ],
        protocol_or_event_check_passed=protocol_passed,
        replay_or_metric_check_passed=metric_passed,
        skipped_checks={
            "real_training": "forbidden for tiny smoke",
            "network": "forbidden for tiny smoke",
            "gpu": "not required for tiny smoke",
            "torch": "not required for tiny smoke",
        },
        elapsed_seconds=max(0.0, time.monotonic() - start),
        errors=errors,
    )
    report = _with_stable_artifact_size(report)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
    return report


def load_tiny_smoke_report(path: str | Path) -> TinySmokeReport:
    return TinySmokeReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _run_protocol_check() -> bool:
    learner_id = normalize_id("learner-0", field_name="learner_id")
    fragment = ModelFragment(
        fragment_id="fragment-0",
        global_version=0,
        vector_data=[0.0, 1.0],
        source_learner_id=learner_id,
        tokens_since_last_sync=8,
        created_at=1,
    )
    heartbeat = LearnerHeartbeat(
        learner_id=learner_id,
        local_step=1,
        tokens_processed=8,
        last_global_version_seen=0,
        status=LearnerStatus.ALIVE,
        throughput_tokens_per_step=8,
        logical_time=1,
    )
    round_id = make_round_id(fragment.global_version)
    quorum = QuorumDecision(
        should_commit=True,
        round_id=round_id,
        current_tick=1,
        accepted_learner_ids=[learner_id],
        reason="synthetic_tiny_smoke",
    )
    merge = MergeDecision(
        round_id=round_id,
        previous_global_version=0,
        new_global_version=1,
        accepted_learner_ids=[learner_id],
        token_weights={learner_id: 1.0},
        useful_tokens=8,
        outer_lr=0.1,
        old_global_vector=[0.0, 0.0],
        weighted_delta=[0.0, 1.0],
        new_global_vector=[0.0, 1.0],
    )
    checkpoint = CheckpointRecord(
        checkpoint_id="checkpoint-0",
        global_version=1,
        logical_time=2,
        global_vector=merge.new_global_vector,
        metrics={"synthetic": True, "useful_tokens": merge.useful_tokens},
    )
    payload: dict[str, Any] = {
        "fragment": fragment.model_dump(mode="json"),
        "heartbeat": heartbeat.model_dump(mode="json"),
        "quorum": quorum.model_dump(mode="json"),
        "merge": merge.model_dump(mode="json"),
        "checkpoint": checkpoint.model_dump(mode="json"),
    }
    digest = sha256_json(payload)
    return round_id == "round-00000001" and len(digest) == 64


def _run_metric_check() -> bool:
    result = validate_report_payload(
        {
            "final_global_version": 1,
            "metrics": {
                "total_tokens_processed": 8,
                "useful_tokens_accepted": 8,
                "wasted_tokens": 0,
                "goodput_ratio": 1.0,
                "global_update_messages_sent": 1,
                "global_update_acks": 1,
                "duplicate_global_update_acks": 0,
                "committed_sync_rounds": 1,
            },
        }
    )
    return result.passed


def _with_stable_artifact_size(report: TinySmokeReport) -> TinySmokeReport:
    current = report
    for _ in range(8):
        size = len(current.to_json().encode("utf-8"))
        if size == current.artifact_bytes:
            return current
        current = current.model_copy(update={"artifact_bytes": size})
    return current
