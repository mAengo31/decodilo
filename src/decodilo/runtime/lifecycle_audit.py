"""Runtime-level lifecycle audit convenience wrappers."""

from __future__ import annotations

from pathlib import Path

from decodilo.storage.artifact_reference_audit import (
    ArtifactReferenceAuditReport,
    audit_artifact_references,
)
from decodilo.syncer.recovery_audit import (
    RecoveryManifestChainReport,
    validate_recovery_manifest_chain,
)


def audit_run_artifacts(workdir: str | Path) -> ArtifactReferenceAuditReport:
    return audit_artifact_references(workdir)


def audit_recovery_chain(workdir: str | Path) -> RecoveryManifestChainReport:
    return validate_recovery_manifest_chain(workdir)
