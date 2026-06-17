"""Lifecycle planning for global state artifact manifests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GlobalStateManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    versions: dict[int, dict]
    latest_version: int


class GlobalStateLifecyclePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    keep_latest_global_states: int = Field(default=2, ge=1)
    retention_version_window: int = Field(default=0, ge=0)
    checkpoint_referenced_versions: set[int] = Field(default_factory=set)
    snapshot_referenced_versions: set[int] = Field(default_factory=set)
    in_flight_versions: set[int] = Field(default_factory=set)


class GlobalStateLifecycleReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    protected_versions: list[int]
    eligible_versions: list[int]
    removed_versions: list[int] = Field(default_factory=list)
    retained_versions: list[int]
    warnings: list[str] = Field(default_factory=list)


def plan_global_state_lifecycle(
    manifest: GlobalStateManifest,
    policy: GlobalStateLifecyclePolicy,
) -> GlobalStateLifecycleReport:
    """Classify global-state versions as protected or GC-eligible."""

    versions = sorted(int(version) for version in manifest.versions)
    latest = manifest.latest_version
    latest_kept = set(versions[-policy.keep_latest_global_states :])
    window_min = max(0, latest - policy.retention_version_window)
    protected = {
        latest,
        *latest_kept,
        *policy.checkpoint_referenced_versions,
        *policy.snapshot_referenced_versions,
        *policy.in_flight_versions,
        *(version for version in versions if version >= window_min),
    }
    protected &= set(versions)
    eligible = [version for version in versions if version not in protected]
    return GlobalStateLifecycleReport(
        protected_versions=sorted(protected),
        eligible_versions=eligible,
        retained_versions=sorted(protected),
    )

