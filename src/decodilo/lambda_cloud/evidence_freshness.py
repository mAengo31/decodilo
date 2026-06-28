"""Freshness checks for M026 Lambda decision evidence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.time_compat import UTC


class LambdaEvidenceFreshnessPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    live_discovery_max_age_hours: float = 24
    price_snapshot_max_age_days: float = 7
    semantic_audit_max_age_hours: float = 24
    final_prelaunch_review_max_age_hours: float = 24
    stale_blocks_m027_authorization: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False


class LambdaEvidenceFreshnessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    freshness_passed: bool
    stale_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_lambda_evidence_freshness(
    *,
    m019c_discovery: str | Path | None = None,
    price_snapshot: str | Path | None = None,
    m025_review: str | Path | None = None,
    semantic_audit: str | Path | None = None,
    policy: LambdaEvidenceFreshnessPolicy | None = None,
    now_utc: datetime | None = None,
) -> LambdaEvidenceFreshnessReport:
    effective_policy = policy or LambdaEvidenceFreshnessPolicy()
    now = now_utc or datetime.now(UTC)
    checks = {
        "m019c_discovery": (m019c_discovery, effective_policy.live_discovery_max_age_hours),
        "price_snapshot": (price_snapshot, effective_policy.price_snapshot_max_age_days * 24),
        "m025_review": (m025_review, effective_policy.final_prelaunch_review_max_age_hours),
        "semantic_audit": (semantic_audit, effective_policy.semantic_audit_max_age_hours),
    }
    missing: list[str] = []
    stale: list[str] = []
    for item_id, (value, max_hours) in checks.items():
        if value is None:
            if item_id in {"m019c_discovery", "price_snapshot", "m025_review"}:
                missing.append(item_id)
            continue
        path = Path(value)
        if not path.exists():
            missing.append(item_id)
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        age_hours = (now - modified).total_seconds() / 3600
        if age_hours > max_hours:
            stale.append(item_id)
    blockers = [f"missing evidence: {item}" for item in missing]
    if effective_policy.stale_blocks_m027_authorization:
        blockers.extend(f"stale evidence: {item}" for item in stale)
    return LambdaEvidenceFreshnessReport(
        freshness_passed=not blockers,
        stale_items=stale,
        missing_items=missing,
        blockers=blockers,
        warnings=[
            "Freshness review is for M027 implementation authorization only; "
            "launch remains disabled."
        ],
    )


def load_lambda_evidence_freshness_report(path: str | Path) -> LambdaEvidenceFreshnessReport:
    return LambdaEvidenceFreshnessReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_evidence_freshness_report(
    path: str | Path,
    report: LambdaEvidenceFreshnessReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
