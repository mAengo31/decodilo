"""Dry-run-first artifact garbage collection."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import InvariantViolation
from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.gc_accounting import ArtifactGCAccountingReport, build_gc_accounting_report
from decodilo.storage.gc_transaction import apply_gc_transaction
from decodilo.storage.lifecycle_policy import ArtifactRetentionPolicy
from decodilo.storage.reachability import build_reachability_graph


class ArtifactGCPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run: bool
    artifacts_scanned: int
    artifacts_live: int
    artifacts_protected: int
    artifacts_orphaned: int
    bytes_reclaimable: int
    delete_candidates: list[str]
    accounting: ArtifactGCAccountingReport | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ArtifactGCReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run: bool
    artifacts_scanned: int
    artifacts_live: int
    artifacts_protected: int
    artifacts_orphaned: int
    bytes_reclaimable: int
    artifacts_deleted: int
    bytes_deleted: int
    transaction_id: str | None = None
    transaction_state: str | None = None
    transaction_log_path: str | None = None
    accounting: ArtifactGCAccountingReport | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def plan_artifact_gc(
    *,
    workdir: str | Path,
    policy: ArtifactRetentionPolicy | None = None,
) -> ArtifactGCPlan:
    policy = policy or ArtifactRetentionPolicy()
    index = build_artifact_index(workdir)
    graph = build_reachability_graph(
        workdir=workdir,
        index=index,
        allow_incomplete=policy.allow_incomplete,
    )
    accounting = build_gc_accounting_report(index=index, graph=graph)
    errors = []
    if graph.unresolved_required and not policy.allow_incomplete:
        errors.extend(f"unresolved required artifact: {path}" for path in graph.unresolved_required)
    temporary = graph.temporary if policy.delete_temporary_artifacts else set()
    candidates = sorted(graph.orphaned | temporary)
    candidates = [path for path in candidates if path not in graph.protected]
    bytes_reclaimable = sum(
        index.artifacts[path].size_bytes for path in candidates if path in index.artifacts
    )
    return ArtifactGCPlan(
        dry_run=policy.dry_run,
        artifacts_scanned=index.artifact_count,
        artifacts_live=len(graph.live),
        artifacts_protected=len(graph.protected),
        artifacts_orphaned=len(graph.orphaned),
        bytes_reclaimable=bytes_reclaimable,
        delete_candidates=candidates,
        accounting=accounting,
        errors=errors,
    )


def run_artifact_gc(
    *,
    workdir: str | Path,
    apply: bool = False,
    policy: ArtifactRetentionPolicy | None = None,
) -> ArtifactGCReport:
    policy = (policy or ArtifactRetentionPolicy()).model_copy(update={"dry_run": not apply})
    plan = plan_artifact_gc(workdir=workdir, policy=policy)
    if plan.errors and not policy.allow_incomplete:
        raise InvariantViolation("; ".join(plan.errors))
    deleted = 0
    bytes_deleted = 0
    transaction_id = None
    transaction_state = None
    transaction_log_path = None
    if apply:
        before_sizes = {
            path: Path(path).stat().st_size
            for path in plan.delete_candidates
            if Path(path).exists() and Path(path).is_file()
        }
        try:
            transaction = apply_gc_transaction(
                workdir=workdir,
                planned_deletes=plan.delete_candidates,
            )
        except InvariantViolation:
            raise
        transaction_id = transaction.transaction_id
        transaction_state = transaction.transaction_state
        transaction_log_path = str(
            Path(workdir) / ".decodilo_gc_transactions" / f"{transaction_id}.json"
        )
        deleted = len(transaction.deleted_paths)
        bytes_deleted = sum(before_sizes.get(path, 0) for path in transaction.deleted_paths)
    return ArtifactGCReport(
        dry_run=not apply,
        artifacts_scanned=plan.artifacts_scanned,
        artifacts_live=plan.artifacts_live,
        artifacts_protected=plan.artifacts_protected,
        artifacts_orphaned=plan.artifacts_orphaned,
        bytes_reclaimable=plan.bytes_reclaimable,
        artifacts_deleted=deleted,
        bytes_deleted=bytes_deleted,
        transaction_id=transaction_id,
        transaction_state=transaction_state,
        transaction_log_path=transaction_log_path,
        accounting=plan.accounting,
        errors=plan.errors,
        warnings=plan.warnings,
    )
