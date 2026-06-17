"""Explicit GC accounting with disjoint reachability and overlay labels."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.artifact_index import ArtifactIndex
from decodilo.storage.reachability import ArtifactReachabilityGraph

ArtifactKind = Literal[
    "manifest",
    "chunk",
    "checkpoint",
    "event_segment",
    "snapshot",
    "report",
    "run_spec",
    "recovery_manifest",
    "global_state",
    "spill",
    "temp",
    "unknown",
]
ReachabilityState = Literal["reachable", "unreachable", "unresolved"]
ProtectionState = Literal["protected", "unprotected"]
RetentionState = Literal["retained", "gc_eligible", "temporary", "orphaned", "deleted"]


class ArtifactClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    path: str
    artifact_kind: ArtifactKind
    reachability_state: ReachabilityState
    protection_state: ProtectionState
    retention_state: RetentionState
    referenced_by: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    byte_size: int = Field(ge=0)


class ArtifactClassificationSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifacts: dict[str, ArtifactClassification] = Field(default_factory=dict)


class ArtifactGCAccountingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifacts_scanned_total: int
    unique_artifacts_scanned: int
    reachable_count: int
    unreachable_count: int
    unresolved_count: int
    protected_count: int
    unprotected_count: int
    retained_count: int
    gc_eligible_count: int
    orphaned_count: int
    temporary_count: int
    deleted_count: int
    bytes_scanned: int
    bytes_reachable: int
    bytes_protected: int
    bytes_gc_eligible: int
    bytes_deleted: int
    disjoint_partition_valid: bool
    overlaps_explained: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    classifications: dict[str, ArtifactClassification] = Field(default_factory=dict)


def artifact_kind_for_path(path: str) -> ArtifactKind:
    target = Path(path)
    name = target.name
    parts = set(target.parts)
    if name == "run_spec.json":
        return "run_spec"
    if name == "report.json":
        return "report"
    if name == "recovery_manifest.json" or "recovery_manifests" in parts:
        return "recovery_manifest"
    if name == "replay_snapshot.json":
        return "snapshot"
    if name == "segments_manifest.json" or name.startswith("segment-"):
        return "event_segment"
    if name.endswith(".artifact.json"):
        return "global_state" if "global" in parts else "manifest"
    if "chunks" in parts:
        return "chunk"
    if "checkpoint" in name:
        return "checkpoint"
    if name.endswith(".tmp"):
        return "temp"
    if "spill" in parts:
        return "spill"
    return "unknown"


def build_gc_accounting_report(
    *,
    index: ArtifactIndex,
    graph: ArtifactReachabilityGraph,
    deleted_paths: set[str] | None = None,
) -> ArtifactGCAccountingReport:
    """Build an unambiguous report from an artifact index and reachability graph."""

    deleted = deleted_paths or set()
    all_paths = set(index.artifacts) | graph.unresolved_required | deleted
    classifications: dict[str, ArtifactClassification] = {}
    for path in sorted(all_paths):
        record = index.artifacts.get(path)
        byte_size = record.size_bytes if record is not None else 0
        if path in graph.unresolved_required and path not in index.artifacts:
            reachability: ReachabilityState = "unresolved"
        elif path in graph.live or path in graph.retained or path in graph.protected:
            reachability = "reachable"
        else:
            reachability = "unreachable"

        protection: ProtectionState = "protected" if path in graph.protected else "unprotected"
        if path in deleted:
            retention: RetentionState = "deleted"
        elif path in graph.temporary:
            retention = "temporary"
        elif path in graph.orphaned:
            retention = "orphaned"
        elif path in graph.live or path in graph.retained or path in graph.protected:
            retention = "retained"
        else:
            retention = "gc_eligible"

        reasons: list[str] = []
        if path in graph.live:
            reasons.append("reachable from run lifecycle")
        if path in graph.protected:
            reasons.append("protected by recovery/report policy")
        if path in graph.retained:
            reasons.append("retained by artifact manifest or segment policy")
        if path in graph.temporary:
            reasons.append("temporary artifact")
        if path in graph.orphaned:
            reasons.append("unreferenced by lifecycle manifests")
        if path in graph.unresolved_required:
            reasons.append("required reference is unresolved")

        classifications[path] = ArtifactClassification(
            artifact_id=path,
            path=path,
            artifact_kind=artifact_kind_for_path(path),
            reachability_state=reachability,
            protection_state=protection,
            retention_state=retention,
            referenced_by=[],
            reasons=reasons,
            byte_size=byte_size,
        )

    reachable = [
        item for item in classifications.values() if item.reachability_state == "reachable"
    ]
    unreachable = [
        item for item in classifications.values() if item.reachability_state == "unreachable"
    ]
    unresolved = [
        item for item in classifications.values() if item.reachability_state == "unresolved"
    ]
    protected = [
        item for item in classifications.values() if item.protection_state == "protected"
    ]
    gc_eligible = [
        item
        for item in classifications.values()
        if item.retention_state in {"gc_eligible", "temporary", "orphaned"}
        and item.protection_state == "unprotected"
    ]
    unique = len(classifications)
    disjoint_valid = len(reachable) + len(unreachable) + len(unresolved) == unique
    errors = [] if disjoint_valid else ["reachability partition does not sum to scanned total"]
    return ArtifactGCAccountingReport(
        artifacts_scanned_total=unique,
        unique_artifacts_scanned=unique,
        reachable_count=len(reachable),
        unreachable_count=len(unreachable),
        unresolved_count=len(unresolved),
        protected_count=len(protected),
        unprotected_count=unique - len(protected),
        retained_count=sum(
            item.retention_state == "retained" for item in classifications.values()
        ),
        gc_eligible_count=len(gc_eligible),
        orphaned_count=sum(
            item.retention_state == "orphaned" for item in classifications.values()
        ),
        temporary_count=sum(
            item.retention_state == "temporary" for item in classifications.values()
        ),
        deleted_count=sum(item.retention_state == "deleted" for item in classifications.values()),
        bytes_scanned=sum(item.byte_size for item in classifications.values()),
        bytes_reachable=sum(item.byte_size for item in reachable),
        bytes_protected=sum(item.byte_size for item in protected),
        bytes_gc_eligible=sum(item.byte_size for item in gc_eligible),
        bytes_deleted=sum(
            item.byte_size
            for item in classifications.values()
            if item.retention_state == "deleted"
        ),
        disjoint_partition_valid=disjoint_valid,
        overlaps_explained=[
            "protection_state is an overlay on reachability and retention",
            "retained/protected artifacts are reachable policy labels, not extra totals",
        ],
        errors=errors,
        classifications=classifications,
    )

