"""Calibration helpers for learner-pod scaling estimates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.runtime.perf_characterization import load_performance_characterization


def calibration_from_perf_report(path: str | Path) -> dict[str, Any]:
    report = load_performance_characterization(path)
    useful_tps = report.derived.get("useful_tokens_per_second") or 0.0
    learners = max(1, report.learner_count)
    return {
        "per_learner_token_rate": useful_tps / learners if useful_tps else None,
        "observed_artifact_io_time_fraction": report.derived.get(
            "artifact_io_time_fraction"
        ),
        "observed_merge_time_fraction": report.derived.get("merge_time_fraction"),
        "source_report": str(path),
    }

