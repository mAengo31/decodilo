"""Risk register for future remote backend implementation review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskCategory = Literal[
    "security",
    "integrity",
    "consistency",
    "lifecycle",
    "cost",
    "performance",
    "operational",
    "credential",
    "replay_recovery",
    "vendor_lock_in",
    "data_exfiltration",
]
RiskSeverity = Literal["low", "medium", "high", "critical"]
RiskLikelihood = Literal["low", "medium", "high"]
RiskStatus = Literal["open", "mitigated", "accepted", "blocked"]


class RemoteBackendRiskMitigation(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str
    evidence_refs: list[str] = Field(default_factory=list)


class RemoteBackendRisk(BaseModel):
    model_config = ConfigDict(frozen=True)

    risk_id: str
    category: RiskCategory
    severity: RiskSeverity
    likelihood: RiskLikelihood
    description: str
    affected_requirements: list[str] = Field(default_factory=list)
    mitigation: RemoteBackendRiskMitigation
    owner: str | None = None
    status: RiskStatus = "open"
    evidence_refs: list[str] = Field(default_factory=list)
    blocks_sdk_addition: bool = True


class RemoteBackendRiskRegister(BaseModel):
    model_config = ConfigDict(frozen=True)

    register_schema_version: int = 1
    proposal_ref: str | None = None
    risks: list[RemoteBackendRisk]
    blockers: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_default_remote_backend_risk_register(
    *,
    proposal_ref: str | None = None,
) -> RemoteBackendRiskRegister:
    risks = [
        _risk("credential_leakage", "credential", "critical", "credential leakage"),
        _risk("overbroad_credentials", "credential", "high", "overbroad credentials"),
        _risk("stale_manifest_read", "consistency", "high", "stale manifest read"),
        _risk("corrupted_artifact_read", "integrity", "critical", "corrupted artifact read"),
        _risk(
            "unauthorized_artifact_delete",
            "security",
            "critical",
            "unauthorized artifact delete",
        ),
        _risk("partial_write_visibility", "integrity", "high", "partial write visibility"),
        _risk(
            "gc_deletes_live_artifact",
            "lifecycle",
            "critical",
            "lifecycle GC deleting live artifact",
        ),
        _risk("runaway_storage_cost", "cost", "high", "runaway storage cost"),
        _risk("bandwidth_saturation", "performance", "high", "bandwidth saturation"),
        _risk("backend_throttling", "performance", "high", "backend throttling"),
        _risk(
            "replay_wrong_version",
            "replay_recovery",
            "critical",
            "replay using wrong artifact version",
        ),
        _risk(
            "data_exfiltration",
            "data_exfiltration",
            "critical",
            "data exfiltration through artifact access",
        ),
        _risk("missing_audit_logs", "operational", "high", "missing audit logs"),
        _risk(
            "orphaned_cloud_resources",
            "operational",
            "critical",
            "orphaned cloud resources if coupled to launcher in future",
        ),
    ]
    return _build_register(proposal_ref=proposal_ref, risks=risks)


def update_remote_backend_risk_register(
    *,
    proposal_ref: str | None,
    risks: list[RemoteBackendRisk],
) -> RemoteBackendRiskRegister:
    return _build_register(proposal_ref=proposal_ref, risks=risks)


def load_remote_backend_risk_register(path: str | Path) -> RemoteBackendRiskRegister:
    return RemoteBackendRiskRegister.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_risk_register(
    path: str | Path,
    register: RemoteBackendRiskRegister,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(register.to_json(), encoding="utf-8")


def _risk(
    risk_id: str,
    category: RiskCategory,
    severity: RiskSeverity,
    description: str,
) -> RemoteBackendRisk:
    return RemoteBackendRisk(
        risk_id=risk_id,
        category=category,
        severity=severity,
        likelihood="medium",
        description=description,
        affected_requirements=["remote_backend"],
        mitigation=RemoteBackendRiskMitigation(
            description="must be mitigated with evidence before SDK review"
        ),
        blocks_sdk_addition=severity == "critical",
    )


def _build_register(
    *,
    proposal_ref: str | None,
    risks: list[RemoteBackendRisk],
) -> RemoteBackendRiskRegister:
    blockers = [
        risk.risk_id
        for risk in risks
        if risk.blocks_sdk_addition and risk.severity == "critical" and risk.status == "open"
    ]
    return RemoteBackendRiskRegister(
        proposal_ref=proposal_ref,
        risks=risks,
        blockers=blockers,
    )
