"""CI-safe local soak runner."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from decodilo.runtime.fault_matrix import _case_config
from decodilo.runtime.local_runner import LocalRunConfig, LocalRunner


def run_local_soak(
    *,
    base_config: LocalRunConfig,
    cases: list[str],
    long: bool = False,
    profile: str = "custom",
    trainer: str | None = None,
) -> dict[str, Any]:
    base_config.workdir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    results: dict[str, Any] = {}
    total_rounds = 0
    total_tokens = 0
    replay_failures = 0
    metric_failures = 0
    for case in cases:
        workdir = base_config.workdir / case
        if case == "baseline":
            kwargs = dict(base_config.__dict__)
            kwargs["workdir"] = workdir
            kwargs["report_json"] = workdir / "report.json"
            kwargs["run_id"] = f"{base_config.run_id or 'soak'}-baseline"
            config = LocalRunConfig(**kwargs)
        else:
            config = _case_config(case=case, base=base_config, workdir=workdir)
        if long:
            kwargs = dict(config.__dict__)
            kwargs["steps"] = max(config.steps, base_config.steps * 3)
            config = LocalRunConfig(**kwargs)
        report = LocalRunner(config).run()
        replay_passed = report.replay_validation.replay_passed
        metric_passed = bool(report.metric_validation.get("passed"))
        rounds = int(report.metrics.get("committed_sync_rounds", 0))
        tokens = int(report.metrics.get("useful_tokens_accepted", 0))
        total_rounds += rounds
        total_tokens += tokens
        replay_failures += 0 if replay_passed else 1
        metric_failures += 0 if metric_passed else 1
        results[case] = {
            "report_json": str(config.report_json),
            "committed_sync_rounds": rounds,
            "useful_tokens_accepted": tokens,
            "replay_passed": replay_passed,
            "metric_validation_passed": metric_passed,
            "passed": replay_passed and metric_passed,
        }
    summary = {
        "profile": profile,
        "trainer": trainer or base_config.trainer_type,
        "cases_run": len(cases),
        "cases_passed": sum(1 for result in results.values() if result["passed"]),
        "cases_failed": sum(1 for result in results.values() if not result["passed"]),
        "total_committed_sync_rounds": total_rounds,
        "total_useful_tokens": total_tokens,
        "total_wall_time_seconds": time.monotonic() - started,
        "replay_failures": replay_failures,
        "metric_validation_failures": metric_failures,
        "artifact_paths": [result["report_json"] for result in results.values()],
        "cases": results,
    }
    (base_config.workdir / "soak_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def load_soak_summary(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
