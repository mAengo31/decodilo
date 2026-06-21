"""Remote backend readiness gate.

This gate is intentionally unable to enable a real remote backend in this
milestone. The highest status it can emit is implementation_review_required.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.storage.remote_backend_conformance import RemoteBackendConformanceReport
from decodilo.storage.remote_backend_evidence import RemoteBackendEvidencePackage
from decodilo.storage.remote_backend_security import RemoteBackendSecurityReport


class RemoteBackendReadinessStatus(str, Enum):
    not_started = "not_started"
    evidence_missing = "evidence_missing"
    simulation_only = "simulation_only"
    conformance_failed = "conformance_failed"
    conformance_passed_simulator_only = "conformance_passed_simulator_only"
    implementation_review_required = "implementation_review_required"
    sdk_addition_allowed_by_policy = "sdk_addition_allowed_by_policy"
    real_backend_enabled = "real_backend_enabled"


_DISALLOWED_M016_STATUSES = {
    RemoteBackendReadinessStatus.sdk_addition_allowed_by_policy,
    RemoteBackendReadinessStatus.real_backend_enabled,
}


class RemoteBackendReadinessCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: str
    passed: bool
    blocker: bool = True
    evidence_ref: str | None = None
    notes: list[str] = Field(default_factory=list)


class RemoteBackendReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scenario_id: str
    source_scaling_report_ref: str | None = None
    requirement_ref: str | None = None
    validation_report_ref: str | None = None
    conformance_report_ref: str | None = None
    evidence_package_ref: str | None = None
    criteria: list[RemoteBackendReadinessCriterion]
    passed_criteria: list[str]
    failed_criteria: list[str]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    readiness_status: RemoteBackendReadinessStatus
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _forbid_enabled_status(self) -> RemoteBackendReadinessReport:
        if self.readiness_status in _DISALLOWED_M016_STATUSES:
            raise ValueError(
                "M016 readiness gate cannot allow SDK addition or real backend enablement"
            )
        if self.remote_backend_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("readiness reports must not enable backend or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class RemoteBackendReadinessGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    gate_schema_version: int = 1
    required_criteria: list[str] = Field(
        default_factory=lambda: [
            "learner_scaling_report_exists",
            "backend_design_targets_exist",
            "remote_requirements_generated",
            "remote_design_validation_report_exists",
            "conformance_suite_completed",
            "threat_model_completed",
            "security_checklist_completed",
            "credentials_model_completed",
            "auth_scope_model_completed",
            "encryption_policy_completed",
            "integrity_policy_completed",
            "idempotency_policy_completed",
            "lifecycle_policy_completed",
            "replay_restore_policy_completed",
            "cost_model_completed",
            "bandwidth_accounting_completed",
            "preflight_report_completed",
            "no_raw_secrets_present",
            "no_real_sdk_dependency_added",
            "no_network_calls_required",
            "remote_backend_remains_disabled",
            "cloud_launch_remains_disabled",
        ]
    )


def evaluate_remote_backend_readiness(
    *,
    scenario_id: str,
    source_scaling_report_ref: str | None,
    requirement_ref: str | None,
    validation_report_ref: str | None,
    conformance_report_ref: str | None,
    conformance_report: RemoteBackendConformanceReport | None,
    security_report: RemoteBackendSecurityReport | None,
    evidence_package: RemoteBackendEvidencePackage | None,
    evidence_package_ref: str | None = None,
    credentials_model_completed: bool = True,
    auth_scope_model_completed: bool = True,
    encryption_policy_completed: bool = True,
    integrity_policy_completed: bool = True,
    idempotency_policy_completed: bool = True,
    lifecycle_policy_completed: bool = True,
    replay_restore_policy_completed: bool = True,
    cost_model_completed: bool = True,
    bandwidth_accounting_completed: bool = True,
    preflight_report_completed: bool = True,
    raw_secret_detected: bool = False,
    sdk_dependency_detected: bool = False,
    network_calls_required: bool = False,
) -> RemoteBackendReadinessReport:
    criteria: list[RemoteBackendReadinessCriterion] = []

    def add(criterion_id: str, passed: bool, evidence_ref: str | None = None) -> None:
        criteria.append(
            RemoteBackendReadinessCriterion(
                criterion_id=criterion_id,
                passed=passed,
                evidence_ref=evidence_ref,
            )
        )

    add(
        "learner_scaling_report_exists",
        source_scaling_report_ref is not None,
        source_scaling_report_ref,
    )
    add(
        "backend_design_targets_exist",
        source_scaling_report_ref is not None,
        source_scaling_report_ref,
    )
    add("remote_requirements_generated", requirement_ref is not None, requirement_ref)
    add(
        "remote_design_validation_report_exists",
        validation_report_ref is not None,
        validation_report_ref,
    )
    add(
        "conformance_suite_completed",
        conformance_report is not None,
        conformance_report_ref,
    )
    add("threat_model_completed", security_report is not None)
    add("security_checklist_completed", security_report is not None and security_report.passed)
    add("credentials_model_completed", credentials_model_completed)
    add("auth_scope_model_completed", auth_scope_model_completed)
    add("encryption_policy_completed", encryption_policy_completed)
    add("integrity_policy_completed", integrity_policy_completed)
    add("idempotency_policy_completed", idempotency_policy_completed)
    add("lifecycle_policy_completed", lifecycle_policy_completed)
    add("replay_restore_policy_completed", replay_restore_policy_completed)
    add("cost_model_completed", cost_model_completed)
    add("bandwidth_accounting_completed", bandwidth_accounting_completed)
    add("preflight_report_completed", preflight_report_completed)
    add("no_raw_secrets_present", not raw_secret_detected)
    add("no_real_sdk_dependency_added", not sdk_dependency_detected)
    add("no_network_calls_required", not network_calls_required)
    add("remote_backend_remains_disabled", True)
    add("cloud_launch_remains_disabled", True)
    if evidence_package is not None:
        add(
            "evidence_package_complete",
            evidence_package.manifest.evidence_completeness_score >= 1.0
            and not evidence_package.manifest.blockers,
            evidence_package_ref,
        )

    blockers = [criterion.criterion_id for criterion in criteria if not criterion.passed]
    warnings = ["passing simulator conformance does not permit SDK addition"]
    if conformance_report is None:
        status = RemoteBackendReadinessStatus.evidence_missing
    elif not conformance_report.passed:
        status = RemoteBackendReadinessStatus.conformance_failed
    elif blockers:
        status = RemoteBackendReadinessStatus.evidence_missing
    else:
        status = RemoteBackendReadinessStatus.implementation_review_required
    return RemoteBackendReadinessReport(
        scenario_id=scenario_id,
        source_scaling_report_ref=source_scaling_report_ref,
        requirement_ref=requirement_ref,
        validation_report_ref=validation_report_ref,
        conformance_report_ref=conformance_report_ref,
        evidence_package_ref=evidence_package_ref,
        criteria=criteria,
        passed_criteria=[criterion.criterion_id for criterion in criteria if criterion.passed],
        failed_criteria=blockers,
        blockers=blockers,
        warnings=warnings,
        readiness_status=status,
    )


def load_remote_backend_readiness_report(path: str | Path) -> RemoteBackendReadinessReport:
    return RemoteBackendReadinessReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_readiness_report(
    path: str | Path,
    report: RemoteBackendReadinessReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
