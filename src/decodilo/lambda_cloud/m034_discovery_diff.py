"""Read-only discovery diffing for M034C incident closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger

LambdaM034DiscoveryDiffConfidence = Literal[
    "high_no_instance_created",
    "likely_no_instance_created",
    "uncertain",
    "possible_instance_created",
]


class LambdaM034DiscoveryDiffReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    pre_instance_count: int
    post_instance_count: int
    closeout_instance_count: int | None = None
    new_instances_detected: list[dict[str, Any]] = Field(default_factory=list)
    disappeared_instances: list[dict[str, Any]] = Field(default_factory=list)
    billable_state_instances: list[dict[str, Any]] = Field(default_factory=list)
    unmanaged_instances: list[dict[str, Any]] = Field(default_factory=list)
    possible_owned_candidates: list[dict[str, Any]] = Field(default_factory=list)
    confidence: LambdaM034DiscoveryDiffConfidence
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034DiscoveryDiffReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034 discovery diff cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m034_discovery_diff(
    *,
    pre_discovery: dict[str, Any],
    post_discovery: dict[str, Any],
    ledger: LambdaM029LaunchLedger | None = None,
    closeout_discovery: dict[str, Any] | None = None,
) -> LambdaM034DiscoveryDiffReport:
    pre_instances = _instances(pre_discovery)
    post_instances = _instances(post_discovery)
    closeout_instances = (
        _instances(closeout_discovery) if closeout_discovery is not None else None
    )
    baseline = {_instance_key(item) for item in pre_instances}
    post_keys = {_instance_key(item) for item in post_instances}
    new_instances = [item for item in post_instances if _instance_key(item) not in baseline]
    disappeared = [item for item in pre_instances if _instance_key(item) not in post_keys]
    visible = closeout_instances if closeout_instances is not None else post_instances
    owned_id = ledger.owned_instance_id if ledger is not None else None
    billable = [item for item in visible if _is_billable_state(item)]
    unmanaged = [
        item
        for item in visible
        if _instance_key(item)
        and _instance_key(item) != (owned_id or "")
        and _is_billable_state(item)
    ]
    candidates = [item for item in new_instances if _is_billable_state(item)]
    warnings: list[str] = []
    if not pre_instances and not post_instances and not closeout_instances:
        confidence: LambdaM034DiscoveryDiffConfidence = "high_no_instance_created"
    elif candidates:
        confidence = "possible_instance_created"
        warnings.append("new billable instance candidate appeared after M034C request")
    elif disappeared:
        confidence = "uncertain"
        warnings.append("instance disappeared before ownership was recorded")
    elif billable:
        confidence = "uncertain"
        warnings.append("billable instance visible during M034C incident diff")
    else:
        confidence = "likely_no_instance_created"
    if unmanaged:
        warnings.append("unmanaged billable instance requires manual review")
    return LambdaM034DiscoveryDiffReport(
        pre_instance_count=len(pre_instances),
        post_instance_count=len(post_instances),
        closeout_instance_count=None if closeout_instances is None else len(closeout_instances),
        new_instances_detected=new_instances,
        disappeared_instances=disappeared,
        billable_state_instances=billable,
        unmanaged_instances=unmanaged,
        possible_owned_candidates=candidates,
        confidence=confidence,
        warnings=warnings,
    )


def build_lambda_m034_discovery_diff_from_paths(
    *,
    pre_discovery: str | Path,
    post_discovery: str | Path,
    ledger: str | Path | None = None,
    closeout_discovery: str | Path | None = None,
) -> LambdaM034DiscoveryDiffReport:
    ledger_obj = None
    if ledger is not None and Path(ledger).exists():
        ledger_obj = LambdaM029LaunchLedger.model_validate_json(
            Path(ledger).read_text(encoding="utf-8")
        )
    return build_lambda_m034_discovery_diff(
        pre_discovery=_load_json(pre_discovery),
        post_discovery=_load_json(post_discovery),
        closeout_discovery=None
        if closeout_discovery is None
        else _load_json(closeout_discovery),
        ledger=ledger_obj,
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _instances(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    instances = report.get("instances") or report.get("discovered_instances") or []
    return [item for item in instances if isinstance(item, dict)]


def _instance_key(instance: dict[str, Any]) -> str:
    value = (
        instance.get("instance_id")
        or instance.get("id")
        or instance.get("name")
        or instance.get("hostname")
        or ""
    )
    return str(value)


def _is_billable_state(instance: dict[str, Any]) -> bool:
    state = str(
        instance.get("status")
        or instance.get("state")
        or instance.get("lifecycle_state")
        or ""
    ).lower()
    return state in {"running", "pending", "booting", "active", "launching"}


def load_lambda_m034_discovery_diff(path: str | Path) -> LambdaM034DiscoveryDiffReport:
    return LambdaM034DiscoveryDiffReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_discovery_diff(
    path: str | Path,
    report: LambdaM034DiscoveryDiffReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
