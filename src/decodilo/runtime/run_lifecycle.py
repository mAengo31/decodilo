"""Run inspection, validation, and non-destructive compaction utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.artifact_manifest import (
    ArtifactManifest,
    artifact_record,
    validate_artifact_manifest,
)
from decodilo.runtime.metrics_validation import validate_report_payload
from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.artifact_reference_audit import audit_artifact_references
from decodilo.storage.gc import ArtifactGCPlan, plan_artifact_gc
from decodilo.storage.gc_safety import failed_gc_transactions
from decodilo.storage.lifecycle_policy import ArtifactRetentionPolicy
from decodilo.syncer.event_segments import EventSegmentRotationPolicy, segment_events_from_jsonl
from decodilo.syncer.idempotency_compaction import (
    IdempotencyCompactionPolicy,
    compact_idempotency_store,
)
from decodilo.syncer.idempotency_store import IdempotencyStore
from decodilo.syncer.recovery_audit import validate_recovery_manifest_chain
from decodilo.syncer.recovery_manifest import load_recovery_manifest
from decodilo.syncer.replay import replay_event_log
from decodilo.syncer.replay_snapshot import (
    load_replay_snapshot,
    make_replay_snapshot,
    write_replay_snapshot,
)


class RunInspectSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str | None
    mode: str | None
    trainer: str | None
    global_version: int
    committed_sync_rounds: int
    artifact_count: int
    checkpoint_count: int
    event_segment_count: int
    latest_recovery_manifest: str | None
    preflight_status: str


class RunValidateSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_artifacts: list[str] = Field(default_factory=list)


class RunCompactReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    idempotency_compaction_report: dict[str, Any]
    replay_snapshot_path: str | None
    event_segment_manifest_path: str | None
    gc_plan_ref: str | None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def inspect_run(workdir: str | Path) -> RunInspectSummary:
    root = Path(workdir)
    report = _read_json(root / "report.json")
    run_spec = _read_json(root / "run_spec.json")
    index = build_artifact_index(root)
    event_segments = sorted((root / "event_segments").glob("segment-*.jsonl"))
    recovery = root / "recovery_manifest.json"
    checkpoints = [
        path
        for path in root.rglob("*checkpoint*")
        if path.is_file() and not path.name.endswith(".tmp")
    ]
    return RunInspectSummary(
        run_id=(report or run_spec or {}).get("run_id"),
        mode=(run_spec or {}).get("mode") or (report or {}).get("mode"),
        trainer=(run_spec or {}).get("trainer_type") or (report or {}).get("trainer_type"),
        global_version=int(report.get("final_global_version", 0)) if report else 0,
        committed_sync_rounds=int(
            report.get("metrics", {}).get("committed_sync_rounds", 0)
        )
        if report
        else 0,
        artifact_count=index.artifact_count,
        checkpoint_count=len(checkpoints),
        event_segment_count=len(event_segments),
        latest_recovery_manifest=str(recovery) if recovery.exists() else None,
        preflight_status="unknown",
    )


def validate_run(workdir: str | Path, *, replay: bool = True) -> RunValidateSummary:
    root = Path(workdir)
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    report_path = root / "report.json"
    if report_path.exists():
        checked.append(str(report_path))
        validation = validate_report_payload(_read_json(report_path))
        if not validation.passed:
            errors.extend(validation.errors)
    else:
        errors.append("missing report.json")
    artifact_path = root / "artifacts.json"
    if artifact_path.exists():
        checked.append(str(artifact_path))
        manifest = ArtifactManifest.model_validate_json(artifact_path.read_text(encoding="utf-8"))
        artifact_errors = validate_artifact_manifest(manifest)
        errors.extend(artifact_errors)
        checked.extend(record.path for record in manifest.artifacts.values())
    else:
        errors.append("missing artifacts.json")
    recovery_path = root / "recovery_manifest.json"
    if recovery_path.exists():
        checked.append(str(recovery_path))
        try:
            load_recovery_manifest(recovery_path)
        except Exception as exc:  # noqa: BLE001 - validation report should retain context
            errors.append(f"invalid recovery_manifest.json: {exc}")
    else:
        warnings.append("recovery_manifest.json not present")
    segments_manifest = root / "event_segments" / "segments_manifest.json"
    if segments_manifest.exists():
        checked.append(str(segments_manifest))
        from decodilo.syncer.event_segments import EventSegmentReader

        try:
            EventSegmentReader(segments_manifest).validate()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid event segment chain: {exc}")
    snapshot_path = root / "replay_snapshot.json"
    if snapshot_path.exists():
        checked.append(str(snapshot_path))
        try:
            load_replay_snapshot(snapshot_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid replay_snapshot.json: {exc}")
    if recovery_path.exists():
        chain = validate_recovery_manifest_chain(root)
        if not chain.passed:
            errors.extend(f"recovery chain: {error}" for error in chain.errors)
    audit = audit_artifact_references(root)
    if not audit.passed:
        errors.extend(f"artifact audit: {error}" for error in audit.errors)
        errors.extend(
            f"artifact audit: untracked artifact: {path}"
            for path in audit.untracked_artifacts
        )
    failed_transactions = failed_gc_transactions(root)
    if failed_transactions:
        errors.extend(f"failed gc transaction: {tx}" for tx in failed_transactions)
    if replay and (root / "events.jsonl").exists():
        try:
            replay_event_log(root / "events.jsonl")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"replay failed: {exc}")
    return RunValidateSummary(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
    )


def compact_run(workdir: str | Path, *, out: str | Path | None = None) -> RunCompactReport:
    """Write replay snapshot/event segments and a dry-run GC plan."""

    root = Path(workdir)
    warnings: list[str] = []
    errors: list[str] = []
    idempotency_report: dict[str, Any]
    store = IdempotencyStore(run_id=_run_id(root) or "unknown")
    compacted, report = compact_idempotency_store(
        store,
        IdempotencyCompactionPolicy(global_version_watermark=0, logical_time_watermark=0),
        current_global_version=0,
    )
    _ = compacted
    idempotency_report = report.model_dump(mode="json")

    snapshot_path: Path | None = None
    segment_manifest_path: Path | None = None
    event_log_path = root / "events.jsonl"
    if event_log_path.exists():
        try:
            replay_state = replay_event_log(event_log_path)
            segment_manifest = segment_events_from_jsonl(
                event_log_path=event_log_path,
                out_dir=root / "event_segments",
                policy=EventSegmentRotationPolicy(max_events_per_segment=10),
            )
            segment_manifest_path = root / "event_segments" / "segments_manifest.json"
            snapshot = make_replay_snapshot(
                run_id=_run_id(root) or "unknown",
                global_version=(
                    replay_state.global_versions[-1] if replay_state.global_versions else 0
                ),
                logical_time=_last_logical_time(event_log_path),
                last_event_id=_last_event_id(event_log_path),
                committed_rounds=replay_state.sync_rounds_committed,
                useful_tokens_accepted=replay_state.accepted_useful_tokens,
                global_vector=replay_state.final_global_vector,
                last_segment_id=(
                    segment_manifest.segments[-1].segment_id
                    if segment_manifest.segments
                    else None
                ),
            )
            snapshot_path = root / "replay_snapshot.json"
            write_replay_snapshot(snapshot_path, snapshot)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"snapshot compaction failed: {exc}")
    else:
        warnings.append("events.jsonl not present")

    gc_plan_path = root / "gc_plan.json"
    gc_plan: ArtifactGCPlan = plan_artifact_gc(
        workdir=root,
        policy=ArtifactRetentionPolicy(dry_run=True, allow_incomplete=True),
    )
    gc_plan_path.write_text(
        json.dumps(gc_plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    compact_report = RunCompactReport(
        idempotency_compaction_report=idempotency_report,
        replay_snapshot_path=str(snapshot_path) if snapshot_path else None,
        event_segment_manifest_path=(
            str(segment_manifest_path) if segment_manifest_path else None
        ),
        gc_plan_ref=str(gc_plan_path),
        warnings=warnings,
        errors=errors,
    )
    if out is not None:
        Path(out).write_text(
            json.dumps(compact_report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _refresh_artifact_manifest(root)
    return compact_report


def refresh_lifecycle_artifact_manifest(workdir: str | Path) -> None:
    """Record lifecycle artifacts such as preflight, compact, and GC reports."""

    _refresh_artifact_manifest(Path(workdir))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_id(root: Path) -> str | None:
    report = _read_json(root / "report.json")
    spec = _read_json(root / "run_spec.json")
    return report.get("run_id") or spec.get("run_id")


def _last_event_id(path: Path) -> str:
    last: str | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = json.loads(line)["event_id"]
    return last or "none:00000000:none"


def _last_logical_time(path: Path) -> int:
    last = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = int(json.loads(line)["logical_time"])
    return last


def _refresh_artifact_manifest(root: Path) -> None:
    manifest_path = root / "artifacts.json"
    if not manifest_path.exists():
        return
    manifest = ArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    lifecycle_paths = [
        *sorted((root / "recovery_manifests").glob("*.json")),
        *sorted((root / "event_segments").glob("segment-*.jsonl")),
        root / "event_segments" / "segments_manifest.json",
        root / "replay_snapshot.json",
        *sorted(root.glob("compact_report*.json")),
        *sorted(root.glob("gc_plan*.json")),
        *sorted(root.glob("artifact_audit*.json")),
        *sorted(root.glob("preflight*.json")),
    ]
    artifacts = dict(manifest.artifacts)
    lifecycle = list(manifest.lifecycle_artifact_paths)
    for path in lifecycle_paths:
        if not path.exists():
            continue
        path_str = str(path)
        artifacts[path_str] = artifact_record(path)
        if path_str not in lifecycle:
            lifecycle.append(path_str)
    refreshed = manifest.model_copy(
        update={
            "artifacts": artifacts,
            "lifecycle_artifact_paths": sorted(lifecycle),
        }
    )
    manifest_path.write_text(
        json.dumps(refreshed.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
