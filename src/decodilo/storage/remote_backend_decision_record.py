"""Decision record for future remote backend SDK review."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.storage.remote_backend_risk_register import RemoteBackendRiskRegister
from decodilo.storage.remote_backend_sdk_guard import RemoteBackendSDKGuardReport


class RemoteBackendDecisionStatus(str, Enum):
    rejected = "rejected"
    needs_more_evidence = "needs_more_evidence"
    candidate_for_future_sdk_review = "candidate_for_future_sdk_review"
    blocked_by_risk = "blocked_by_risk"
    blocked_by_missing_capability = "blocked_by_missing_capability"
    blocked_by_missing_evidence = "blocked_by_missing_evidence"
    sdk_addition_allowed_by_policy = "sdk_addition_allowed_by_policy"
    real_backend_enabled = "real_backend_enabled"
    launch_ready = "launch_ready"
    launch_allowed = "launch_allowed"


_FORBIDDEN_DECISION_STATUSES = {
    RemoteBackendDecisionStatus.sdk_addition_allowed_by_policy,
    RemoteBackendDecisionStatus.real_backend_enabled,
    RemoteBackendDecisionStatus.launch_ready,
    RemoteBackendDecisionStatus.launch_allowed,
}


class RemoteBackendDecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str
    proposal_ref: str
    evidence_package_ref: str
    readiness_report_ref: str
    conformance_report_ref: str | None = None
    risk_register_ref: str
    provider_assessment_ref: str | None = None
    rollout_plan_ref: str | None = None
    sdk_guard_report_ref: str
    status: RemoteBackendDecisionStatus
    rationale: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_evidence: list[str] = Field(default_factory=list)
    human_reviewer_required: bool = True
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _forbid_enabled_status(self) -> RemoteBackendDecisionRecord:
        if self.status in _FORBIDDEN_DECISION_STATUSES:
            raise ValueError("M017 decision record cannot allow SDK addition or backend enablement")
        if self.remote_backend_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("decision record cannot enable backend or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_decision_record(
    *,
    proposal_ref: str,
    evidence_package_ref: str,
    readiness_report_ref: str,
    risk_register_ref: str,
    sdk_guard_report_ref: str,
    sdk_guard_report: RemoteBackendSDKGuardReport,
    risk_register: RemoteBackendRiskRegister,
    conformance_report_ref: str | None = None,
    provider_assessment_ref: str | None = None,
    rollout_plan_ref: str | None = None,
    evidence_complete: bool = True,
) -> RemoteBackendDecisionRecord:
    blockers: list[str] = []
    next_required: list[str] = []
    if not evidence_complete:
        blockers.append("required evidence missing")
        next_required.append("complete evidence package")
        status = RemoteBackendDecisionStatus.needs_more_evidence
    elif not sdk_guard_report.passed:
        blockers.extend(sdk_guard_report.errors)
        next_required.append("remove forbidden SDK/import/env/secret findings")
        status = RemoteBackendDecisionStatus.blocked_by_missing_capability
    elif risk_register.blockers:
        blockers.extend(risk_register.blockers)
        next_required.append("mitigate critical open risks")
        status = RemoteBackendDecisionStatus.blocked_by_risk
    else:
        status = RemoteBackendDecisionStatus.candidate_for_future_sdk_review
    return RemoteBackendDecisionRecord(
        decision_id=f"{Path(proposal_ref).stem}-decision",
        proposal_ref=proposal_ref,
        evidence_package_ref=evidence_package_ref,
        readiness_report_ref=readiness_report_ref,
        conformance_report_ref=conformance_report_ref,
        risk_register_ref=risk_register_ref,
        provider_assessment_ref=provider_assessment_ref,
        rollout_plan_ref=rollout_plan_ref,
        sdk_guard_report_ref=sdk_guard_report_ref,
        status=status,
        rationale=(
            "review-only decision; candidate status does not allow SDK addition"
            if status == RemoteBackendDecisionStatus.candidate_for_future_sdk_review
            else "blocked until evidence or risk conditions are resolved"
        ),
        blockers=blockers,
        warnings=["future SDK review candidate only; backend remains disabled"],
        next_required_evidence=next_required,
    )


def load_remote_backend_decision_record(path: str | Path) -> RemoteBackendDecisionRecord:
    return RemoteBackendDecisionRecord.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_decision_record(
    path: str | Path,
    record: RemoteBackendDecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
