"""Helpers for comparing genesis and snapshot replay."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from decodilo.syncer.replay import replay_event_log
from decodilo.syncer.replay_snapshot import replay_from_snapshot_and_segments


class ReplayComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    genesis_final_global_version: int
    snapshot_final_global_version: int
    genesis_useful_tokens_accepted: int
    snapshot_useful_tokens_accepted: int
    replay_start_mode: str
    errors: list[str] = []


def compare_genesis_and_snapshot_replay(workdir: str | Path) -> ReplayComparisonReport:
    root = Path(workdir)
    errors: list[str] = []
    genesis = replay_event_log(root / "events.jsonl")
    snapshot = replay_from_snapshot_and_segments(
        snapshot_path=root / "replay_snapshot.json",
        segment_manifest_path=root / "event_segments" / "segments_manifest.json",
        artifact_workdir=root,
    )
    genesis_version = genesis.global_versions[-1] if genesis.global_versions else 0
    snapshot_version = snapshot.global_versions[-1] if snapshot.global_versions else 0
    if genesis_version != snapshot_version:
        errors.append("final global_version differs")
    if genesis.accepted_useful_tokens != snapshot.accepted_useful_tokens:
        errors.append("useful token count differs")
    return ReplayComparisonReport(
        passed=not errors,
        genesis_final_global_version=genesis_version,
        snapshot_final_global_version=snapshot_version,
        genesis_useful_tokens_accepted=genesis.accepted_useful_tokens,
        snapshot_useful_tokens_accepted=snapshot.accepted_useful_tokens,
        replay_start_mode="snapshot",
        errors=errors,
    )

