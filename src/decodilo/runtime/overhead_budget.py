"""Overhead budget checks for performance characterization reports."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.perf_characterization import PerformanceCharacterizationReport


class OverheadBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_encode_time_fraction: float | None = None
    max_artifact_io_time_fraction: float | None = None
    max_merge_time_fraction: float | None = None
    max_checkpoint_time_fraction: float | None = None
    max_replay_time_fraction: float | None = None
    max_lifecycle_validation_time_fraction: float | None = None
    max_artifact_bytes_per_useful_token: float | None = None
    max_total_wall_time_seconds: float | None = None
    fail_on_budget_exceeded: bool = True


class OverheadBudgetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    checked: dict[str, float | None] = Field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_overhead_budget(path: str | Path) -> OverheadBudget:
    return OverheadBudget.model_validate_json(Path(path).read_text(encoding="utf-8"))


def check_overhead_budget(
    *,
    report: PerformanceCharacterizationReport,
    budget: OverheadBudget,
) -> OverheadBudgetResult:
    errors: list[str] = []
    warnings: list[str] = []
    checked: dict[str, float | None] = {}
    mapping = {
        "encode_time_fraction": budget.max_encode_time_fraction,
        "artifact_io_time_fraction": budget.max_artifact_io_time_fraction,
        "merge_time_fraction": budget.max_merge_time_fraction,
        "checkpoint_time_fraction": budget.max_checkpoint_time_fraction,
        "replay_time_fraction": budget.max_replay_time_fraction,
        "lifecycle_validation_time_fraction": budget.max_lifecycle_validation_time_fraction,
        "artifact_bytes_per_useful_token": budget.max_artifact_bytes_per_useful_token,
    }
    for metric, limit in mapping.items():
        if limit is None:
            continue
        value = report.derived.get(metric)
        checked[metric] = value
        _compare(metric, value, limit, budget.fail_on_budget_exceeded, errors, warnings)
    if budget.max_total_wall_time_seconds is not None:
        value = report.timing.get("total_wall_time_seconds")
        checked["total_wall_time_seconds"] = value
        _compare(
            "total_wall_time_seconds",
            value,
            budget.max_total_wall_time_seconds,
            budget.fail_on_budget_exceeded,
            errors,
            warnings,
        )
    return OverheadBudgetResult(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        checked=checked,
    )


def _compare(
    metric: str,
    value: float | None,
    limit: float,
    fail: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    if value is None:
        message = f"{metric} is missing"
        (errors if fail else warnings).append(message)
        return
    if value > limit:
        message = f"{metric}={value:.6g} exceeds budget {limit:.6g}"
        (errors if fail else warnings).append(message)


def write_overhead_budget_result(path: str | Path, result: OverheadBudgetResult) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.to_json(), encoding="utf-8")
