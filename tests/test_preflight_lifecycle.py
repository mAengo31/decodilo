import json
import subprocess
import sys

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.runtime.preflight import run_local_preflight
from decodilo.storage.checksums import sha256_file
from decodilo.syncer.recovery_manifest import (
    make_recovery_manifest,
    write_recovery_manifest_atomic,
)

pytestmark = [pytest.mark.unit, pytest.mark.storage]


def test_local_preflight_fails_missing_recovery_manifest_for_chunked_run(tmp_path) -> None:
    (tmp_path / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": "run-preflight",
                "seed": 1,
                "learners": 1,
                "steps": 1,
                "min_quorum": 1,
                "grace_window": 0,
                "max_staleness_versions": 1,
                "vector_dim": 1,
                "num_fragments": 1,
                "local_steps_per_sync": 1,
                "checkpoint_storage_mode": "chunked",
                "payload_storage_mode": "chunked",
                "merge_mode": "streaming_chunked",
                "global_update_storage_mode": "chunked",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "report.json").write_text(
        json.dumps(
            {
                "run_id": "run-preflight",
                "final_global_version": 0,
                "metrics": {
                    "total_tokens_processed": 0,
                    "useful_tokens_accepted": 0,
                    "wasted_tokens": 0,
                    "goodput_ratio": 0.0,
                    "committed_sync_rounds": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "artifacts.json").write_text(
        json.dumps(
            {
                "run_id": "run-preflight",
                "workdir": str(tmp_path),
                "run_spec_path": str(tmp_path / "run_spec.json"),
                "report_path": str(tmp_path / "report.json"),
                "event_log_path": str(tmp_path / "events.jsonl"),
                "syncer_checkpoint_paths": [],
                "learner_checkpoint_paths": [],
                "learner_log_paths": [],
                "spill_artifact_paths": [],
                "price_snapshot_paths": [],
                "budget_manifest_path": None,
                "recovery_manifest_path": None,
                "artifacts": {},
                "created_at_utc": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    result = run_local_preflight(workdir=tmp_path)

    assert result.preflight_passed is False
    assert any("recovery_manifest" in error for error in result.errors)


def test_local_preflight_fails_broken_recovery_chain(tmp_path) -> None:
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    event_log = tmp_path / "events.jsonl"
    checkpoint = tmp_path / "syncer_checkpoint.json"
    run_spec.write_text(
        json.dumps(
            {
                "run_id": "run-preflight-chain",
                "seed": 1,
                "learners": 1,
                "steps": 1,
                "min_quorum": 1,
                "grace_window": 0,
                "max_staleness_versions": 1,
                "vector_dim": 1,
                "num_fragments": 1,
                "local_steps_per_sync": 1,
                "checkpoint_storage_mode": "chunked",
                "payload_storage_mode": "chunked",
                "merge_mode": "streaming_chunked",
                "global_update_storage_mode": "chunked",
            }
        ),
        encoding="utf-8",
    )
    report.write_text(
        json.dumps(
            {
                "run_id": "run-preflight-chain",
                "final_global_version": 0,
                "metrics": {
                    "total_tokens_processed": 0,
                    "useful_tokens_accepted": 0,
                    "wasted_tokens": 0,
                    "goodput_ratio": 0.0,
                    "committed_sync_rounds": 0,
                    "global_update_messages_sent": 0,
                    "global_update_acks": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    event_log.write_text("", encoding="utf-8")
    checkpoint.write_text('{"ok": true}\n', encoding="utf-8")
    manifest = make_recovery_manifest(
        run_id="run-preflight-chain",
        manifest_id="recovery-1",
        created_logical_time=1,
        global_version=1,
        checkpoint_ref={"path": str(checkpoint)},
        checkpoint_storage_mode="chunked",
        recovery_source="chunked",
        required_artifact_hashes={str(checkpoint): sha256_file(checkpoint)},
        previous_recovery_manifest_hash="missing-previous",
    )
    versioned = tmp_path / "recovery_manifests" / "recovery-1.json"
    write_recovery_manifest_atomic(versioned, manifest)
    write_recovery_manifest_atomic(tmp_path / "recovery_manifest.json", manifest)
    artifact_manifest = build_artifact_manifest(
        run_id="run-preflight-chain",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=event_log,
        syncer_checkpoint_paths=[checkpoint],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
        recovery_manifest_path=tmp_path / "recovery_manifest.json",
        lifecycle_artifact_paths=[versioned],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", artifact_manifest)

    result = run_local_preflight(workdir=tmp_path)

    assert result.preflight_passed is False
    assert any("recovery chain" in error for error in result.errors)


def test_preflight_out_is_tracked_in_artifact_manifest(tmp_path) -> None:
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    event_log = tmp_path / "events.jsonl"
    run_spec.write_text(
        json.dumps(
            {
                "run_id": "run-preflight-out",
                "seed": 1,
                "learners": 1,
                "steps": 1,
                "min_quorum": 1,
                "grace_window": 0,
                "max_staleness_versions": 1,
                "vector_dim": 1,
                "num_fragments": 1,
                "local_steps_per_sync": 1,
            }
        ),
        encoding="utf-8",
    )
    report.write_text(
        json.dumps(
            {
                "run_id": "run-preflight-out",
                "final_global_version": 0,
                "metrics": {
                    "total_tokens_processed": 0,
                    "useful_tokens_accepted": 0,
                    "wasted_tokens": 0,
                    "goodput_ratio": 0.0,
                    "committed_sync_rounds": 0,
                    "global_update_messages_sent": 0,
                    "global_update_acks": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    event_log.write_text("", encoding="utf-8")
    artifact_manifest = build_artifact_manifest(
        run_id="run-preflight-out",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=event_log,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", artifact_manifest)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "preflight",
            "local",
            "--workdir",
            str(tmp_path),
            "--out",
            str(tmp_path / "preflight.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    audit = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "artifacts",
            "audit",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(audit.stdout)["passed"] is True
