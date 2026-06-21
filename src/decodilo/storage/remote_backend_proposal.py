"""Review-only implementation proposal for a future remote artifact backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.storage.remote_backend_evidence import RemoteBackendEvidencePackage
from decodilo.storage.remote_backend_provider_matrix import (
    RemoteBackendProviderCandidate,
    RemoteBackendProviderComparisonMatrix,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_sdk_guard import scan_json_for_secret_like_values


class RemoteBackendImplementationScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)


class RemoteBackendImplementationNonGoals(BaseModel):
    model_config = ConfigDict(frozen=True)

    no_cloud_launch: bool = True
    no_real_backend_enablement: bool = True
    no_credentials: bool = True
    no_production_use: bool = True
    notes: list[str] = Field(default_factory=list)


class RemoteBackendImplementationPhase(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase_id: str
    description: str
    current_phase: bool = False
    remote_backend_enabled: bool = False
    allowed_operations: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)


class RemoteBackendImplementationDependencyPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposed_sdk_name: str | None = None
    proposed_sdk_version_constraint: str | None = None
    import_allowed_in_current_milestone: bool = False
    dependency_addition_allowed: bool = False
    notes: list[str] = Field(default_factory=list)


class RemoteBackendImplementationEvidenceRefs(BaseModel):
    model_config = ConfigDict(frozen=True)

    readiness_report_ref: str
    evidence_package_ref: str
    conformance_report_ref: str
    requirement_ref: str
    provider_matrix_ref: str | None = None


class RemoteBackendImplementationProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_schema_version: int = 1
    proposal_id: str
    provider_candidate_name: str
    backend_type: str
    source_readiness_report_ref: str
    source_evidence_package_ref: str
    source_conformance_report_ref: str
    source_requirement_ref: str
    source_provider_matrix_ref: str | None = None
    target_learner_count: int = Field(gt=0)
    stress_learner_count: int = Field(gt=0)
    target_read_gbps: float = Field(ge=0)
    target_write_gbps: float = Field(ge=0)
    target_ops_per_second: float = Field(ge=0)
    target_checkpoint_growth_gb_per_hour: float = Field(ge=0)
    target_replay_snapshot_frequency: str
    dependency_plan: RemoteBackendImplementationDependencyPlan
    proposed_auth_model: dict[str, Any] = Field(default_factory=dict)
    proposed_encryption_model: dict[str, Any] = Field(default_factory=dict)
    proposed_integrity_model: dict[str, Any] = Field(default_factory=dict)
    proposed_lifecycle_model: dict[str, Any] = Field(default_factory=dict)
    proposed_cost_model: dict[str, Any] = Field(default_factory=dict)
    proposed_observability_model: dict[str, Any] = Field(default_factory=dict)
    proposed_failure_model: dict[str, Any] = Field(default_factory=dict)
    proposed_rollout_phases: list[RemoteBackendImplementationPhase] = Field(
        default_factory=list
    )
    explicit_non_goals: RemoteBackendImplementationNonGoals = Field(
        default_factory=RemoteBackendImplementationNonGoals
    )
    required_human_reviews: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled_and_secret_free(self) -> RemoteBackendImplementationProposal:
        if self.remote_backend_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("proposal cannot enable backend or launch")
        findings = scan_json_for_secret_like_values(self.model_dump(mode="json"))
        if findings:
            raise ValueError(f"proposal contains raw secret-like values: {findings}")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_implementation_proposal(
    *,
    requirements: RemoteBackendRequirementSet,
    evidence_package: RemoteBackendEvidencePackage,
    provider_matrix: RemoteBackendProviderComparisonMatrix,
    provider_name: str,
    readiness_report_ref: str,
    evidence_package_ref: str,
    conformance_report_ref: str,
    requirement_ref: str,
    provider_matrix_ref: str | None = None,
    proposed_sdk_name: str | None = None,
    proposed_sdk_version_constraint: str | None = None,
) -> RemoteBackendImplementationProposal:
    provider = _select_provider(provider_matrix, provider_name)
    blockers: list[str] = []
    warnings = [
        "review-only proposal; no SDK import or remote backend enablement is allowed",
    ]
    if evidence_package.manifest.evidence_completeness_score < 1.0:
        blockers.append("evidence package incomplete")
    if evidence_package.manifest.blockers:
        blockers.extend(evidence_package.manifest.blockers)
    phases = [
        RemoteBackendImplementationPhase(
            phase_id="phase_0_design_only",
            description="Current milestone review-only design package.",
            current_phase=True,
            allowed_operations=["read local evidence", "write review artifacts"],
            forbidden_operations=["import remote SDK", "read credentials", "network calls"],
            required_evidence=["M016 evidence package", "SDK guard report"],
        )
    ]
    return RemoteBackendImplementationProposal(
        proposal_id=f"{requirements.scenario_id}-{provider.provider_name}-proposal",
        provider_candidate_name=provider.provider_name,
        backend_type=provider.backend_type,
        source_readiness_report_ref=readiness_report_ref,
        source_evidence_package_ref=evidence_package_ref,
        source_conformance_report_ref=conformance_report_ref,
        source_requirement_ref=requirement_ref,
        source_provider_matrix_ref=provider_matrix_ref,
        target_learner_count=requirements.target_learner_count,
        stress_learner_count=requirements.stress_learner_count,
        target_read_gbps=requirements.peak_artifact_read_gbps,
        target_write_gbps=requirements.peak_artifact_write_gbps,
        target_ops_per_second=requirements.peak_artifact_ops_per_second,
        target_checkpoint_growth_gb_per_hour=(
            requirements.checkpoint_storage_growth_gb_per_hour
        ),
        target_replay_snapshot_frequency=requirements.required_replay_snapshot_frequency,
        dependency_plan=RemoteBackendImplementationDependencyPlan(
            proposed_sdk_name=proposed_sdk_name,
            proposed_sdk_version_constraint=proposed_sdk_version_constraint,
            notes=["metadata only; SDK is not imported or validated"],
        ),
        proposed_auth_model={"scoped_credentials_required": True},
        proposed_encryption_model={
            "encryption_in_transit_required": True,
            "encryption_at_rest_required": True,
        },
        proposed_integrity_model={
            "content_hash_required": True,
            "conditional_manifest_put_required": True,
        },
        proposed_lifecycle_model={"delete_transaction_log_required": True},
        proposed_cost_model={"manual_cost_estimate_required": True},
        proposed_observability_model={"audit_log_required": True},
        proposed_failure_model={"retry_and_idempotency_required": True},
        proposed_rollout_phases=phases,
        explicit_non_goals=RemoteBackendImplementationNonGoals(
            notes=[
                "no cloud launch",
                "no real backend enablement",
                "no credentials",
                "no production use",
            ]
        ),
        required_human_reviews=["security", "infrastructure", "cost", "operations"],
        blockers=blockers,
        warnings=warnings,
    )


def load_remote_backend_implementation_proposal(
    path: str | Path,
) -> RemoteBackendImplementationProposal:
    return RemoteBackendImplementationProposal.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_remote_backend_implementation_proposal(
    path: str | Path,
    proposal: RemoteBackendImplementationProposal,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(proposal.to_json(), encoding="utf-8")


def _select_provider(
    provider_matrix: RemoteBackendProviderComparisonMatrix,
    provider_name: str,
) -> RemoteBackendProviderCandidate:
    for provider in provider_matrix.providers:
        if provider.provider_name == provider_name:
            return provider
    raise ValueError(f"provider candidate not found: {provider_name}")
