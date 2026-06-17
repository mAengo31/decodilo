"""Performance harness report models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PerfOverheadReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    config: dict[str, Any]
    trainer_type: str
    codec_modes: dict[str, str]
    logical_metrics: dict[str, Any]
    runtime_perf_counters: dict[str, Any]
    artifact_metrics: dict[str, Any]
    merge_metrics: dict[str, Any]
    checkpoint_metrics: dict[str, Any]
    replay_metrics: dict[str, Any]
    overhead_breakdown: dict[str, float]
    derived_ratios: dict[str, float]
    validation: dict[str, bool]
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def write_perf_report(path: str | Path, report: PerfOverheadReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
