"""Filesystem artifact indexing for local run directories."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.checksums import sha256_file


class ArtifactIndexRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    size_bytes: int
    sha256: str | None
    artifact_type: str
    exists: bool = True


class ArtifactIndex(BaseModel):
    model_config = ConfigDict(frozen=True)

    workdir: str
    artifacts: dict[str, ArtifactIndexRecord] = Field(default_factory=dict)

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)


def _artifact_type(path: Path) -> str:
    name = path.name
    if name == "run_spec.json":
        return "run_spec"
    if name == "report.json":
        return "report"
    if name == "artifacts.json":
        return "artifact_manifest"
    if name == "recovery_manifest.json":
        return "recovery_manifest"
    if name == "segments_manifest.json":
        return "event_segment_manifest"
    if name.endswith(".artifact.json"):
        return "storage_artifact_manifest"
    if "checkpoint" in name:
        return "checkpoint"
    if name.endswith(".jsonl"):
        return "event_log"
    if name.endswith(".tmp"):
        return "temporary"
    return "file"


def build_artifact_index(workdir: str | Path) -> ArtifactIndex:
    root = Path(workdir)
    records: dict[str, ArtifactIndexRecord] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path)
        records[rel] = ArtifactIndexRecord(
            path=rel,
            size_bytes=path.stat().st_size,
            sha256=sha256_file(path),
            artifact_type=_artifact_type(path),
        )
    return ArtifactIndex(workdir=str(root), artifacts=records)

