"""Artifact manifest and SHA-256 helpers for local runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.pricing.provenance import utc_now_iso


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str | None = None
    exists: bool


class ArtifactManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workdir: str
    run_spec_path: str
    report_path: str
    event_log_path: str
    syncer_checkpoint_paths: list[str] = Field(default_factory=list)
    learner_checkpoint_paths: list[str] = Field(default_factory=list)
    learner_log_paths: list[str] = Field(default_factory=list)
    spill_artifact_paths: list[str] = Field(default_factory=list)
    price_snapshot_paths: list[str] = Field(default_factory=list)
    budget_manifest_path: str | None = None
    recovery_manifest_path: str | None = None
    lifecycle_artifact_paths: list[str] = Field(default_factory=list)
    artifacts: dict[str, ArtifactRecord] = Field(default_factory=dict)
    created_at_utc: str


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: str | Path) -> ArtifactRecord:
    target = Path(path)
    return ArtifactRecord(
        path=str(target),
        exists=target.exists(),
        sha256=sha256_file(target) if target.exists() and target.is_file() else None,
    )


def build_artifact_manifest(
    *,
    run_id: str,
    workdir: str | Path,
    run_spec_path: str | Path,
    report_path: str | Path,
    event_log_path: str | Path,
    syncer_checkpoint_paths: list[str | Path],
    learner_checkpoint_paths: list[str | Path],
    learner_log_paths: list[str | Path],
    price_snapshot_paths: list[str | Path],
    spill_artifact_paths: list[str | Path] | None = None,
    budget_manifest_path: str | Path | None = None,
    recovery_manifest_path: str | Path | None = None,
    lifecycle_artifact_paths: list[str | Path] | None = None,
) -> ArtifactManifest:
    paths = [run_spec_path, report_path, event_log_path]
    paths.extend(syncer_checkpoint_paths)
    paths.extend(learner_checkpoint_paths)
    paths.extend(learner_log_paths)
    paths.extend(spill_artifact_paths or [])
    paths.extend(price_snapshot_paths)
    if budget_manifest_path is not None:
        paths.append(budget_manifest_path)
    if recovery_manifest_path is not None:
        paths.append(recovery_manifest_path)
    paths.extend(lifecycle_artifact_paths or [])
    artifacts = {str(path): artifact_record(path) for path in paths}
    return ArtifactManifest(
        run_id=run_id,
        workdir=str(workdir),
        run_spec_path=str(run_spec_path),
        report_path=str(report_path),
        event_log_path=str(event_log_path),
        syncer_checkpoint_paths=[str(path) for path in syncer_checkpoint_paths],
        learner_checkpoint_paths=[str(path) for path in learner_checkpoint_paths],
        learner_log_paths=[str(path) for path in learner_log_paths],
        spill_artifact_paths=[str(path) for path in (spill_artifact_paths or [])],
        price_snapshot_paths=[str(path) for path in price_snapshot_paths],
        budget_manifest_path=str(budget_manifest_path) if budget_manifest_path else None,
        recovery_manifest_path=(
            str(recovery_manifest_path) if recovery_manifest_path else None
        ),
        lifecycle_artifact_paths=[str(path) for path in (lifecycle_artifact_paths or [])],
        artifacts=artifacts,
        created_at_utc=utc_now_iso(),
    )


def write_artifact_manifest(path: str | Path, manifest: ArtifactManifest) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_artifact_manifest(manifest: ArtifactManifest) -> list[str]:
    errors: list[str] = []
    for record in manifest.artifacts.values():
        if not record.exists:
            errors.append(f"missing artifact: {record.path}")
        elif record.sha256 and sha256_file(record.path) != record.sha256:
            errors.append(f"artifact hash mismatch: {record.path}")
    return errors
