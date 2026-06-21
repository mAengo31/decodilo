"""Stable learner scaling decision reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.pod_count_optimizer import PodCountOptimizationResult


class LearnerScalingDecisionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    created_at_utc: str | None = None
    scenario: dict[str, Any]
    calibration_profile: dict[str, Any] = Field(default_factory=dict)
    objective: str
    candidates: list[dict[str, Any]]
    recommended_learner_count: int | None
    recommended_quorum: int | None
    recommended_grace_window: float | None
    recommended_sync_interval: int | None
    recommended_fragment_count: int | None = None
    expected_goodput: float | None
    expected_useful_tokens_per_second: float | None
    expected_cost_per_useful_token: float | None
    expected_cost_per_sample_efficiency_adjusted_token: float | None
    dominant_bottleneck: str | None
    backend_design_targets: dict[str, Any]
    sensitivity_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    cloud_state: dict[str, bool] = Field(
        default_factory=lambda: {"launch_ready": False, "launch_allowed": False}
    )

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_scaling_decision_report(
    *,
    scenario: LearnerPodScalingScenario,
    optimization: PodCountOptimizationResult,
) -> LearnerScalingDecisionReport:
    recommended = optimization.recommended_candidate
    warnings: list[str] = []
    for candidate in optimization.candidates:
        warnings.extend(candidate.warnings)
    targets = _backend_targets(optimization)
    return LearnerScalingDecisionReport(
        created_at_utc=datetime.now(UTC).isoformat(),
        scenario=scenario.model_dump(mode="json"),
        calibration_profile=scenario.calibration_profile,
        objective=optimization.objective,
        candidates=[candidate.model_dump(mode="json") for candidate in optimization.candidates],
        recommended_learner_count=optimization.recommended_learner_count,
        recommended_quorum=(
            scenario.min_quorum_for(recommended.learner_count) if recommended else None
        ),
        recommended_grace_window=(
            scenario.grace_window_seconds_for(recommended.learner_count) if recommended else None
        ),
        recommended_sync_interval=scenario.sync_interval_steps if recommended else None,
        recommended_fragment_count=scenario.fragment_count if recommended else None,
        expected_goodput=recommended.estimated_goodput_ratio if recommended else None,
        expected_useful_tokens_per_second=(
            recommended.useful_tokens_per_second if recommended else None
        ),
        expected_cost_per_useful_token=(
            recommended.cost_per_useful_token if recommended else None
        ),
        expected_cost_per_sample_efficiency_adjusted_token=(
            recommended.cost_per_sample_efficiency_adjusted_token if recommended else None
        ),
        dominant_bottleneck=recommended.dominant_bottleneck if recommended else None,
        backend_design_targets=targets,
        sensitivity_summary=optimization.sensitivity_summary,
        warnings=sorted(set(warnings)),
        limitations=[
            "planning and simulation only; no cloud launch is enabled",
            "algorithmic efficiency is a heuristic proxy, not an ML quality guarantee",
            "local overhead calibration may not extrapolate to remote artifact backends",
        ],
    )


def write_scaling_decision_report(path: str | Path, report: LearnerScalingDecisionReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_scaling_decision_report(path: str | Path) -> LearnerScalingDecisionReport:
    return LearnerScalingDecisionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def extract_backend_design_targets(path: str | Path) -> dict[str, Any]:
    report = load_scaling_decision_report(path)
    return {
        **report.backend_design_targets,
        "launch_ready": report.cloud_state["launch_ready"],
        "launch_allowed": report.cloud_state["launch_allowed"],
    }


def _backend_targets(optimization: PodCountOptimizationResult) -> dict[str, Any]:
    candidates = optimization.candidates
    selected = optimization.recommended_candidate
    if not candidates:
        return {}
    target_count = (
        selected.learner_count if selected is not None else max(c.learner_count for c in candidates)
    )
    peak_read = max(float(c.artifact_pressure["artifact_read_gbps_required"]) for c in candidates)
    peak_write = max(
        float(c.artifact_pressure["artifact_write_gbps_required"]) for c in candidates
    )
    peak_ops = max(float(c.artifact_pressure["artifact_ops_per_second"]) for c in candidates)
    peak_merge = max(float(c.syncer_pressure["syncer_merge_gbps_required"]) for c in candidates)
    checkpoint_growth = max(
        float(c.artifact_pressure["checkpoint_bytes_per_interval"]) / (1024**3)
        for c in candidates
    )
    return {
        "target_learner_count": target_count,
        "peak_artifact_read_gbps": peak_read,
        "peak_artifact_write_gbps": peak_write,
        "peak_artifact_ops_per_second": peak_ops,
        "peak_syncer_merge_gbps": peak_merge,
        "checkpoint_storage_growth_gb_per_hour": checkpoint_growth,
        "event_log_growth_mb_per_hour": target_count * 0.5,
        "required_replay_snapshot_frequency": "every checkpoint or compaction cycle",
    }

