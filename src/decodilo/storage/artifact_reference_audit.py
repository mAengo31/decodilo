"""Audit local run artifacts and references for lifecycle completeness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.artifact_manifest import ArtifactManifest
from decodilo.storage.checksums import sha256_file


class ArtifactReferenceAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    artifacts_seen: int
    references_checked: int
    missing_references: list[str] = Field(default_factory=list)
    untracked_artifacts: list[str] = Field(default_factory=list)
    checksum_errors: list[str] = Field(default_factory=list)
    outside_workdir_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def audit_artifact_references(workdir: str | Path) -> ArtifactReferenceAuditReport:
    root = Path(workdir).resolve()
    manifest_path = root / "artifacts.json"
    missing: list[str] = []
    untracked: list[str] = []
    checksum_errors: list[str] = []
    outside: list[str] = []
    warnings: list[str] = []
    references = 0
    tracked: set[str] = set()
    tracked_resolved: set[str] = set()
    if manifest_path.exists():
        manifest = ArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        tracked = set(manifest.artifacts)
        tracked_resolved = {str(Path(path).resolve()) for path in tracked}
        for record in manifest.artifacts.values():
            references += 1
            path = Path(record.path)
            if not _inside(root, path):
                outside.append(record.path)
            if not path.exists():
                missing.append(record.path)
            elif record.sha256 and path.is_file() and sha256_file(path) != record.sha256:
                checksum_errors.append(record.path)
    else:
        missing.append(str(manifest_path))

    should_track = [
        *root.rglob("*.artifact.json"),
        *(root / "event_segments").glob("segment-*.jsonl"),
        root / "event_segments" / "segments_manifest.json",
        root / "replay_snapshot.json",
        root / "recovery_manifest.json",
        *root.glob("compact_report*.json"),
        *root.glob("gc_plan*.json"),
        *root.glob("preflight*.json"),
    ]
    for path in sorted({candidate.resolve() for candidate in should_track if candidate.exists()}):
        if str(path.resolve()) not in tracked_resolved:
            untracked.append(str(path))

    for source in [root / "events.jsonl", root / "recovery_manifest.json"]:
        if source.exists():
            refs = _extract_paths(source, root)
            references += len(refs)
            for ref in refs:
                path = Path(ref)
                if not _inside(root, path):
                    outside.append(str(path))
                elif not path.exists():
                    missing.append(str(path))
                elif (
                    str(path.resolve()) not in tracked_resolved
                    and path.name.endswith(".artifact.json")
                ):
                    untracked.append(str(path.resolve()))

    errors = sorted(set(missing + checksum_errors + outside))
    return ArtifactReferenceAuditReport(
        passed=not errors and not untracked,
        artifacts_seen=len(tracked),
        references_checked=references,
        missing_references=sorted(set(missing)),
        untracked_artifacts=sorted(set(untracked)),
        checksum_errors=sorted(set(checksum_errors)),
        outside_workdir_errors=sorted(set(outside)),
        warnings=warnings,
        errors=errors,
    )


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _extract_paths(source: Path, root: Path) -> list[str]:
    paths: list[str] = []
    if source.suffix == ".jsonl":
        lines = source.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.strip():
                paths.extend(_walk_for_paths(json.loads(line), root))
    else:
        paths.extend(_walk_for_paths(json.loads(source.read_text(encoding="utf-8")), root))
    return paths


def _walk_for_paths(value: Any, root: Path) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"manifest_path", "path"} and isinstance(item, str):
                path = Path(item)
                found.append(str(path if path.is_absolute() else root / path))
            else:
                found.extend(_walk_for_paths(item, root))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_for_paths(item, root))
    return found
