"""Manual-only provider comparison matrix for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class ProviderCapabilityDeclaration(BaseModel):
    model_config = ConfigDict(frozen=True)

    read_gbps: float = Field(ge=0)
    write_gbps: float = Field(ge=0)
    ops_per_second: float = Field(ge=0)
    max_put_latency_ms: float | None = Field(default=None, ge=0)
    max_get_latency_ms: float | None = Field(default=None, ge=0)
    max_list_latency_ms: float | None = Field(default=None, ge=0)
    strong_read_after_write: bool = False
    monotonic_manifest_visibility: bool = False
    atomic_manifest_commit: bool = False
    conditional_put: bool = False
    content_hash_validation: bool = True
    encryption_at_rest: bool = False
    encryption_in_transit: bool = True
    authentication: bool = False
    authorization_scopes: bool = False
    idempotent_put: bool = False
    idempotent_delete: bool = False
    lifecycle_delete: bool = False
    retention_policy: bool = False
    transaction_log: bool = False
    object_versioning: bool = False
    cost_score_hint: float | None = Field(default=None, ge=0, le=1)
    operational_complexity_score_hint: float | None = Field(default=None, ge=0, le=1)


class RemoteBackendProviderCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_name: str
    backend_type: str
    manual_capabilities: ProviderCapabilityDeclaration
    manual_cost_profile_ref: str | None = None
    manual_latency_profile_ref: str | None = None
    manual_bandwidth_profile_ref: str | None = None
    regions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    data_source: Literal["manual"] = "manual"
    is_live_validated: bool = False

    @model_validator(mode="after")
    def _manual_only(self) -> RemoteBackendProviderCandidate:
        if self.data_source != "manual":
            raise ValueError("provider matrix accepts manual data only")
        if self.is_live_validated:
            raise ValueError("provider matrix cannot mark providers as live validated")
        return self


class RemoteBackendProviderScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_name: str
    scores: dict[str, float]
    total_score: float
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_live_validated: bool = False


class RemoteBackendProviderComparisonMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    matrix_schema_version: int = 1
    scenario_id: str
    providers: list[RemoteBackendProviderCandidate]
    scores: list[RemoteBackendProviderScore]
    warnings: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_provider_comparison_matrix(
    *,
    requirements: RemoteBackendRequirementSet,
    providers: list[RemoteBackendProviderCandidate],
) -> RemoteBackendProviderComparisonMatrix:
    scores = [_score_provider(requirements, provider) for provider in providers]
    scores.sort(key=lambda item: item.total_score, reverse=True)
    return RemoteBackendProviderComparisonMatrix(
        scenario_id=requirements.scenario_id,
        providers=providers,
        scores=scores,
        warnings=["manual capability input only; no live provider validation"],
    )


def load_provider_candidates(path: str | Path) -> list[RemoteBackendProviderCandidate]:
    payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = payload.get("providers", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ValueError("providers JSON must be a list or contain a providers list")
    return [RemoteBackendProviderCandidate.model_validate(item) for item in raw]


def load_provider_comparison_matrix(path: str | Path) -> RemoteBackendProviderComparisonMatrix:
    return RemoteBackendProviderComparisonMatrix.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_provider_comparison_matrix(
    path: str | Path,
    matrix: RemoteBackendProviderComparisonMatrix,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(matrix.to_json(), encoding="utf-8")


def _score_provider(
    requirements: RemoteBackendRequirementSet,
    provider: RemoteBackendProviderCandidate,
) -> RemoteBackendProviderScore:
    caps = provider.manual_capabilities
    blockers: list[str] = []
    warnings: list[str] = []
    throughput = min(
        _ratio(caps.read_gbps, requirements.peak_artifact_read_gbps),
        _ratio(caps.write_gbps, requirements.peak_artifact_write_gbps),
        _ratio(caps.ops_per_second, requirements.peak_artifact_ops_per_second),
    )
    if caps.read_gbps < requirements.peak_artifact_read_gbps:
        blockers.append("insufficient read bandwidth")
    if caps.write_gbps < requirements.peak_artifact_write_gbps:
        blockers.append("insufficient write bandwidth")
    if caps.ops_per_second < requirements.peak_artifact_ops_per_second:
        blockers.append("insufficient artifact ops/sec")
    latency = _latency_score(caps, requirements)
    consistency = _bool_score(
        [
            caps.strong_read_after_write or not requirements.required_read_after_write_consistency,
            caps.monotonic_manifest_visibility
            or not requirements.required_monotonic_manifest_visibility,
            caps.atomic_manifest_commit or not requirements.required_atomic_manifest_commit,
            caps.conditional_put or not requirements.required_conditional_put,
        ]
    )
    if requirements.required_conditional_put and not caps.conditional_put:
        blockers.append("missing conditional put")
    integrity = _bool_score(
        [
            caps.content_hash_validation or not requirements.required_content_hash_validation,
            caps.object_versioning,
        ]
    )
    security = _bool_score(
        [
            caps.encryption_at_rest or not requirements.required_encryption_at_rest,
            caps.encryption_in_transit or not requirements.required_encryption_in_transit,
            caps.authentication or not requirements.required_authentication,
            caps.authorization_scopes or not requirements.required_authorization_scopes,
        ]
    )
    if requirements.required_authentication and not caps.authentication:
        blockers.append("missing authentication")
    lifecycle = _bool_score(
        [
            caps.lifecycle_delete or not requirements.required_lifecycle_delete,
            caps.retention_policy or not requirements.required_retention_policy,
            caps.transaction_log or not requirements.required_transaction_log,
            caps.idempotent_delete or not requirements.required_idempotent_delete,
        ]
    )
    if requirements.required_transaction_log and not caps.transaction_log:
        blockers.append("missing delete transaction log")
    cost = caps.cost_score_hint if caps.cost_score_hint is not None else 0.5
    complexity = (
        caps.operational_complexity_score_hint
        if caps.operational_complexity_score_hint is not None
        else 0.5
    )
    categories = {
        "throughput": throughput,
        "latency": latency,
        "consistency": consistency,
        "integrity": integrity,
        "security": security,
        "lifecycle": lifecycle,
        "cost": cost,
        "operational_complexity": complexity,
    }
    if provider.is_live_validated:
        warnings.append("live validation is not allowed in this milestone")
    return RemoteBackendProviderScore(
        provider_name=provider.provider_name,
        scores=categories,
        total_score=sum(categories.values()) / len(categories),
        blockers=blockers,
        warnings=warnings,
        is_live_validated=False,
    )


def _ratio(actual: float, required: float) -> float:
    if required <= 0:
        return 1.0
    return min(actual / required, 1.0)


def _latency_score(
    caps: ProviderCapabilityDeclaration,
    requirements: RemoteBackendRequirementSet,
) -> float:
    checks: list[bool] = []
    for actual, maximum in [
        (caps.max_put_latency_ms, requirements.max_put_latency_ms),
        (caps.max_get_latency_ms, requirements.max_get_latency_ms),
        (caps.max_list_latency_ms, requirements.max_list_latency_ms),
    ]:
        if maximum is not None and actual is not None:
            checks.append(actual <= maximum)
    return _bool_score(checks) if checks else 0.5


def _bool_score(values: list[bool]) -> float:
    if not values:
        return 1.0
    return sum(1 for value in values if value) / len(values)
