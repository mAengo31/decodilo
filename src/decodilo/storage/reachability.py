"""Reachability graph for local run artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.artifact_manifest import ArtifactManifest
from decodilo.storage.artifact_index import ArtifactIndex
from decodilo.storage.manifest import StorageArtifactManifest


class ArtifactReachabilityGraph(BaseModel):
    model_config = ConfigDict(frozen=True)

    workdir: str
    live: set[str] = Field(default_factory=set)
    protected: set[str] = Field(default_factory=set)
    retained: set[str] = Field(default_factory=set)
    temporary: set[str] = Field(default_factory=set)
    orphaned: set[str] = Field(default_factory=set)
    unresolved_required: set[str] = Field(default_factory=set)


def _add_if_exists(paths: set[str], path: Path) -> None:
    if path.exists():
        paths.add(str(path))


def _chunk_root_for_manifest(manifest_path: Path, workdir: Path) -> Path:
    resolved = manifest_path.resolve()
    for parent in resolved.parents:
        if parent == workdir.resolve():
            break
        if parent.name == "artifacts":
            return parent / "store"
    sibling = manifest_path.parent / "store"
    if sibling.exists():
        return sibling
    return manifest_path.parent


def _chunk_path(chunk_root: Path, chunk_hash: str) -> Path:
    return chunk_root / "chunks" / chunk_hash[:2] / chunk_hash


def build_reachability_graph(
    *,
    workdir: str | Path,
    index: ArtifactIndex,
    allow_incomplete: bool = False,
) -> ArtifactReachabilityGraph:
    root = Path(workdir)
    live: set[str] = set()
    protected: set[str] = set()
    retained: set[str] = set()
    temporary: set[str] = set()
    unresolved: set[str] = set()

    for name in ("run_spec.json", "report.json", "artifacts.json", "recovery_manifest.json"):
        path = root / name
        if path.exists():
            live.add(str(path))
            protected.add(str(path))
        elif name in {"run_spec.json", "report.json"} and not allow_incomplete:
            unresolved.add(str(path))

    artifact_manifest_path = root / "artifacts.json"
    if artifact_manifest_path.exists():
        try:
            manifest = ArtifactManifest.model_validate_json(
                artifact_manifest_path.read_text(encoding="utf-8")
            )
            for record in manifest.artifacts.values():
                if record.exists:
                    live.add(record.path)
                    retained.add(record.path)
        except Exception:  # noqa: BLE001 - report as unresolved for lifecycle validation
            unresolved.add(str(artifact_manifest_path))

    replay_snapshot = root / "replay_snapshot.json"
    _add_if_exists(live, replay_snapshot)
    _add_if_exists(protected, replay_snapshot)
    event_segment_manifest = root / "event_segments" / "segments_manifest.json"
    _add_if_exists(live, event_segment_manifest)
    _add_if_exists(protected, event_segment_manifest)
    for segment_path in sorted((root / "event_segments").glob("segment-*.jsonl")):
        _add_if_exists(live, segment_path)
        _add_if_exists(retained, segment_path)

    recovery_path = root / "recovery_manifest.json"
    if recovery_path.exists():
        try:
            recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
            checkpoint = recovery.get("checkpoint_ref") or {}
            for key in ("path", "manifest_path"):
                if checkpoint.get(key):
                    candidate = Path(str(checkpoint[key]))
                    if candidate.exists():
                        live.add(str(candidate))
                        protected.add(str(candidate))
                    elif not allow_incomplete:
                        unresolved.add(str(candidate))
            for path_str in recovery.get("required_artifact_hashes", {}):
                candidate = Path(path_str)
                if candidate.exists():
                    live.add(str(candidate))
                    protected.add(str(candidate))
                elif not allow_incomplete:
                    unresolved.add(str(candidate))
        except json.JSONDecodeError:
            unresolved.add(str(recovery_path))

    for path_str, record in index.artifacts.items():
        path = Path(path_str)
        if record.artifact_type == "temporary" or path.name.endswith(".tmp"):
            temporary.add(path_str)
        if record.artifact_type == "storage_artifact_manifest":
            try:
                storage_manifest = StorageArtifactManifest.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except Exception:  # noqa: BLE001 - malformed manifests are unresolved
                if not allow_incomplete:
                    unresolved.add(path_str)
                continue
            manifest_is_protected = path_str in protected
            manifest_is_live = path_str in live or path_str in retained
            if manifest_is_live:
                chunk_root = _chunk_root_for_manifest(path, root)
                for chunk_hash in storage_manifest.chunk_hashes:
                    chunk_path = _chunk_path(chunk_root, chunk_hash)
                    if chunk_path.exists():
                        live.add(str(chunk_path))
                        retained.add(str(chunk_path))
                        if manifest_is_protected:
                            protected.add(str(chunk_path))
                    elif not allow_incomplete:
                        unresolved.add(str(chunk_path))

    known = live | protected | retained | temporary
    orphaned = set(index.artifacts) - known
    return ArtifactReachabilityGraph(
        workdir=str(root),
        live=live,
        protected=protected,
        retained=retained,
        temporary=temporary,
        orphaned=orphaned,
        unresolved_required=unresolved,
    )
