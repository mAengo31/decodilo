"""Deterministic local fault matrix runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decodilo.runtime.chaos_plan import RoundAction, SlowLearnerAction
from decodilo.runtime.local_runner import LocalRunConfig, LocalRunner


def _case_config(
    *,
    case: str,
    base: LocalRunConfig,
    workdir: Path,
) -> LocalRunConfig:
    kwargs = dict(base.__dict__)
    kwargs["workdir"] = workdir
    kwargs["report_json"] = workdir / "report.json"
    kwargs["run_id"] = f"{base.run_id or 'fault'}-{case}"
    if case == "learner_kill":
        kwargs["kill_learner"] = RoundAction("learner-0", after_round=1)
    elif case == "learner_restart":
        kwargs["kill_learner"] = RoundAction("learner-0", after_round=1)
        kwargs["restart_learner"] = RoundAction("learner-0", after_round=2)
    elif case == "slow_restore":
        kwargs["slow_learner"] = SlowLearnerAction("learner-1", after_round=1, factor=0.25)
        kwargs["restore_learner"] = RoundAction("learner-1", after_round=3)
    elif case == "syncer_restart":
        kwargs["syncer_checkpoint_interval_rounds"] = 1
        kwargs["restart_syncer_after_round"] = 2
    elif case == "backpressure":
        kwargs["max_total_inflight_bytes"] = 256
    elif case in {
        "duplicate_fragment",
        "duplicate_update_ack",
        "delayed_fragment",
        "malformed_message",
    }:
        # These are covered by transport-level harness tests; the matrix still
        # produces a local baseline report for summary consistency.
        pass
    else:
        raise ValueError(f"unknown fault matrix case {case!r}")
    return LocalRunConfig(**kwargs)


def run_fault_matrix(
    *,
    base_config: LocalRunConfig,
    cases: list[str],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    base_config.workdir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        case_workdir = base_config.workdir / case
        case_config = _case_config(case=case, base=base_config, workdir=case_workdir)
        report = LocalRunner(case_config).run()
        results[case] = {
            "report_json": str(case_config.report_json),
            "committed_sync_rounds": report.metrics.get("committed_sync_rounds"),
            "useful_tokens_accepted": report.metrics.get("useful_tokens_accepted"),
            "replay_passed": report.replay_validation.replay_passed,
            "metric_validation_passed": report.metric_validation.get("passed"),
            "orphan_cleanup_performed": report.process_summary.orphan_cleanup_performed,
            "passed": report.replay_validation.replay_passed
            and bool(report.metric_validation.get("passed")),
        }
    return {"cases": results}
