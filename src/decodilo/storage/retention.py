"""Retention-policy convenience helpers."""

from __future__ import annotations

from pathlib import Path

from decodilo.storage.gc import ArtifactGCPlan, plan_artifact_gc
from decodilo.storage.lifecycle_policy import ArtifactRetentionPolicy


def build_retention_plan(
    *,
    workdir: str | Path,
    policy: ArtifactRetentionPolicy | None = None,
) -> ArtifactGCPlan:
    return plan_artifact_gc(workdir=workdir, policy=policy or ArtifactRetentionPolicy())

