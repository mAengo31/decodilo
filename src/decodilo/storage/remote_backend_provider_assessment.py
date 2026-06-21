"""Manual provider assessment for future remote backend proposals."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_provider_matrix import (
    RemoteBackendProviderCandidate,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class RemoteBackendProviderAssessmentCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: str
    passed: bool
    score: float = Field(ge=0, le=1)
    blocker: bool = False
    notes: list[str] = Field(default_factory=list)


class RemoteBackendProviderAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_name: str
    backend_type: str
    criteria: list[RemoteBackendProviderAssessmentCriterion]
    total_score: float = Field(ge=0, le=1)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_live_validated: bool = False


class RemoteBackendProviderAssessmentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scenario_id: str
    assessment: RemoteBackendProviderAssessment
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def assess_remote_backend_provider(
    *,
    requirements: RemoteBackendRequirementSet,
    provider: RemoteBackendProviderCandidate,
    manual_risk_annotations: list[str] | None = None,
) -> RemoteBackendProviderAssessmentReport:
    caps = provider.manual_capabilities
    criteria = [
        _criterion(
            "throughput_fit",
            caps.read_gbps >= requirements.peak_artifact_read_gbps
            and caps.write_gbps >= requirements.peak_artifact_write_gbps
            and caps.ops_per_second >= requirements.peak_artifact_ops_per_second,
            min(
                _ratio(caps.read_gbps, requirements.peak_artifact_read_gbps),
                _ratio(caps.write_gbps, requirements.peak_artifact_write_gbps),
                _ratio(caps.ops_per_second, requirements.peak_artifact_ops_per_second),
            ),
            blocker=True,
        ),
        _criterion(
            "conditional_put_support",
            caps.conditional_put,
            float(caps.conditional_put),
            True,
        ),
        _criterion(
            "object_versioning_support",
            caps.object_versioning,
            float(caps.object_versioning),
        ),
        _criterion(
            "auth_scope_support",
            caps.authorization_scopes,
            float(caps.authorization_scopes),
            True,
        ),
        _criterion(
            "encryption_support",
            caps.encryption_at_rest and caps.encryption_in_transit,
            float(caps.encryption_at_rest and caps.encryption_in_transit),
            True,
        ),
        _criterion(
            "lifecycle_delete_transaction_support",
            caps.lifecycle_delete and caps.transaction_log,
            float(caps.lifecycle_delete and caps.transaction_log),
            True,
        ),
        _criterion("range_read_support", True, 1.0),
        _criterion(
            "cost_estimate_fit",
            True,
            caps.cost_score_hint if caps.cost_score_hint is not None else 0.5,
        ),
        _criterion(
            "operational_complexity",
            True,
            (
                caps.operational_complexity_score_hint
                if caps.operational_complexity_score_hint is not None
                else 0.5
            ),
        ),
        _criterion("observability_audit_fit", caps.transaction_log, float(caps.transaction_log)),
        _criterion("local_simulator_coverage_gap", False, 0.0),
        _criterion("live_validation_gap", False, 0.0),
    ]
    blockers = [
        criterion.criterion_id
        for criterion in criteria
        if criterion.blocker and not criterion.passed
    ]
    warnings = ["manual input only; provider is not live validated"]
    warnings.extend(manual_risk_annotations or [])
    total = sum(criterion.score for criterion in criteria) / len(criteria)
    assessment = RemoteBackendProviderAssessment(
        provider_name=provider.provider_name,
        backend_type=provider.backend_type,
        criteria=criteria,
        total_score=total,
        blockers=blockers,
        warnings=warnings,
        is_live_validated=False,
    )
    return RemoteBackendProviderAssessmentReport(
        scenario_id=requirements.scenario_id,
        assessment=assessment,
    )


def load_provider_assessment_report(path: str | Path) -> RemoteBackendProviderAssessmentReport:
    return RemoteBackendProviderAssessmentReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_provider_assessment_report(
    path: str | Path,
    report: RemoteBackendProviderAssessmentReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _criterion(
    criterion_id: str,
    passed: bool,
    score: float,
    blocker: bool = False,
) -> RemoteBackendProviderAssessmentCriterion:
    return RemoteBackendProviderAssessmentCriterion(
        criterion_id=criterion_id,
        passed=passed,
        score=max(0.0, min(score, 1.0)),
        blocker=blocker,
    )


def _ratio(actual: float, required: float) -> float:
    if required <= 0:
        return 1.0
    return min(actual / required, 1.0)
