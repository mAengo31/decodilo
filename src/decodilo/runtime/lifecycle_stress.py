"""Short local lifecycle stress runner."""

from __future__ import annotations

import json
from pathlib import Path

from decodilo.runtime.lifecycle_reports import LifecycleStressReport
from decodilo.runtime.local_runner import LocalRunConfig, LocalRunner
from decodilo.runtime.run_lifecycle import compact_run, validate_run
from decodilo.storage.artifact_reference_audit import audit_artifact_references
from decodilo.storage.gc import ArtifactGCPlan
from decodilo.syncer.replay import replay_event_log
from decodilo.syncer.replay_stress import compare_genesis_and_snapshot_replay


def run_lifecycle_stress(
    *,
    config: LocalRunConfig,
    compact_every_rounds: int,
    snapshot_every_compactions: int,
    gc_plan_every_compactions: int,
    restart_syncer_every_compactions: int | None,
    cycles: int = 2,
    out: str | Path | None = None,
) -> LifecycleStressReport:
    """Run a short local job, then repeatedly compact and validate lifecycle artifacts."""

    stress_config = config
    if restart_syncer_every_compactions:
        stress_config = config.__class__(
            **{
                **config.__dict__,
                "restart_syncer_after_round": compact_every_rounds,
                "syncer_checkpoint_interval_rounds": max(
                    1,
                    config.syncer_checkpoint_interval_rounds,
                ),
            }
        )
    local_report = LocalRunner(stress_config).run()
    checkpoints_written = len(list(config.workdir.rglob("*checkpoint*")))
    idempotency_reports: list[dict[str, int]] = []
    gc_reclaimable = 0
    errors: list[str] = []
    warnings: list[str] = []
    max_segments = 0
    snapshots_written = 0
    gc_plans = 0
    for cycle in range(cycles):
        compact = compact_run(
            config.workdir,
            out=config.workdir / f"compact_report_cycle_{cycle}.json",
        )
        idempotency_reports.append(
            {
                "before": int(
                    compact.idempotency_compaction_report.get("records_before", 0)
                ),
                "after": int(compact.idempotency_compaction_report.get("records_after", 0)),
            }
        )
        if compact.errors:
            errors.extend(compact.errors)
        if compact.replay_snapshot_path:
            snapshots_written += 1
        if compact.gc_plan_ref:
            gc_plans += 1
            gc_plan = ArtifactGCPlan.model_validate_json(
                Path(compact.gc_plan_ref).read_text(encoding="utf-8")
            )
            gc_reclaimable = max(gc_reclaimable, gc_plan.bytes_reclaimable)
        segment_count = len(list((config.workdir / "event_segments").glob("segment-*.jsonl")))
        max_segments = max(max_segments, segment_count)
        validation = validate_run(config.workdir)
        if not validation.passed:
            errors.extend(validation.errors)

    genesis_passed = False
    snapshot_passed = False
    try:
        replay_event_log(config.workdir / "events.jsonl")
        genesis_passed = True
    except Exception as exc:  # noqa: BLE001
        errors.append(f"genesis replay failed: {exc}")
    try:
        comparison = compare_genesis_and_snapshot_replay(config.workdir)
        snapshot_passed = comparison.passed
        errors.extend(comparison.errors)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"snapshot replay failed: {exc}")
    audit = audit_artifact_references(config.workdir)
    if not audit.passed:
        errors.extend(audit.errors)
        errors.extend(f"untracked artifact: {path}" for path in audit.untracked_artifacts)
    run_validation = validate_run(config.workdir)
    report = LifecycleStressReport(
        run_id=local_report.run_id,
        cycles_completed=cycles,
        checkpoints_written=checkpoints_written,
        compactions_performed=cycles,
        snapshots_written=snapshots_written,
        gc_plans_written=gc_plans,
        syncer_restarts=len(local_report.process_summary.syncer_restarts),
        genesis_replay_passed=genesis_passed,
        snapshot_replay_passed=snapshot_passed,
        artifact_audit_passed=audit.passed,
        run_validate_passed=run_validation.passed,
        max_event_segment_count=max_segments,
        idempotency_records_before_after=idempotency_reports,
        gc_reclaimable_bytes=gc_reclaimable,
        warnings=warnings,
        errors=errors,
    )
    if out is not None:
        Path(out).write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report

