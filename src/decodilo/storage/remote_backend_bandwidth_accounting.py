"""Bandwidth accounting model for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendBandwidthAccountingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    learner_count: int = Field(gt=0)
    put_bytes: int = Field(ge=0)
    get_bytes: int = Field(ge=0)
    range_get_bytes: int = Field(ge=0)
    list_ops: int = Field(ge=0)
    delete_ops: int = Field(ge=0)
    retry_overhead_bytes: int = Field(ge=0)
    throttling_overhead_bytes: int = Field(ge=0)
    per_learner_traffic_bytes: int = Field(ge=0)
    syncer_traffic_bytes: int = Field(ge=0)
    replay_traffic_bytes: int = Field(ge=0)
    checkpoint_traffic_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_bandwidth_accounting(
    *,
    learner_count: int,
    per_learner_traffic_bytes: int,
    syncer_traffic_bytes: int,
    replay_traffic_bytes: int,
    checkpoint_traffic_bytes: int,
    retry_overhead_ratio: float = 0.0,
    throttling_overhead_bytes: int = 0,
    list_ops: int = 0,
    delete_ops: int = 0,
) -> RemoteBackendBandwidthAccountingReport:
    if retry_overhead_ratio < 0:
        raise ValueError("retry_overhead_ratio must be nonnegative")
    learner_total = learner_count * per_learner_traffic_bytes
    base = learner_total + syncer_traffic_bytes + replay_traffic_bytes + checkpoint_traffic_bytes
    retry_bytes = int(round(base * retry_overhead_ratio))
    total = base + retry_bytes + throttling_overhead_bytes
    return RemoteBackendBandwidthAccountingReport(
        learner_count=learner_count,
        put_bytes=learner_total + checkpoint_traffic_bytes,
        get_bytes=syncer_traffic_bytes + replay_traffic_bytes,
        range_get_bytes=replay_traffic_bytes,
        list_ops=list_ops,
        delete_ops=delete_ops,
        retry_overhead_bytes=retry_bytes,
        throttling_overhead_bytes=throttling_overhead_bytes,
        per_learner_traffic_bytes=learner_total,
        syncer_traffic_bytes=syncer_traffic_bytes,
        replay_traffic_bytes=replay_traffic_bytes,
        checkpoint_traffic_bytes=checkpoint_traffic_bytes,
        total_bytes=total,
        warnings=["planning estimate; no live backend traffic was measured"],
    )


def load_remote_backend_bandwidth_accounting(
    path: str | Path,
) -> RemoteBackendBandwidthAccountingReport:
    return RemoteBackendBandwidthAccountingReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_remote_backend_bandwidth_accounting(
    path: str | Path,
    report: RemoteBackendBandwidthAccountingReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
