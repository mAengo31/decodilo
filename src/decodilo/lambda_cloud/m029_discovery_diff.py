"""Read-only discovery diffing for M029 incident closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger

LambdaM029DiscoveryDiffConfidence = Literal[
    "high_no_instance_created",
    "likely_no_instance_created",
    "uncertain",
    "possible_instance_created",
]


class LambdaM029DiscoveryDiffReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    pre_instance_count: int
    post_instance_count: int
    later_instance_count: int | None = None
    new_instances_detected: list[dict[str, Any]] = Field(default_factory=list)
    disappeared_instances: list[dict[str, Any]] = Field(default_factory=list)
    billable_state_instances: list[dict[str, Any]] = Field(default_factory=list)
    unmanaged_instances: list[dict[str, Any]] = Field(default_factory=list)
    possible_owned_candidates: list[dict[str, Any]] = Field(default_factory=list)
    confidence: LambdaM029DiscoveryDiffConfidence
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_discovery_diff(
    *,
    pre_discovery: dict[str, Any],
    post_discovery: dict[str, Any],
    ledger: LambdaM029LaunchLedger,
    later_discovery: dict[str, Any] | None = None,
) -> LambdaM029DiscoveryDiffReport:
    pre_instances = _instances(pre_discovery)
    post_instances = _instances(post_discovery)
    later_instances = _instances(later_discovery) if later_discovery is not None else None
    baseline = {_instance_key(item) for item in pre_instances}
    post_keys = {_instance_key(item) for item in post_instances}
    new_instances = [item for item in post_instances if _instance_key(item) not in baseline]
    disappeared = [item for item in pre_instances if _instance_key(item) not in post_keys]
    visible = later_instances if later_instances is not None else post_instances
    billable = [item for item in visible if _is_billable_state(item)]
    unmanaged = [
        item
        for item in visible
        if _instance_key(item)
        and _instance_key(item) != (ledger.owned_instance_id or "")
        and _is_billable_state(item)
    ]
    candidates = [item for item in new_instances if _is_billable_state(item)]
    warnings: list[str] = []
    if not pre_instances and not post_instances and not later_instances:
        confidence: LambdaM029DiscoveryDiffConfidence = "high_no_instance_created"
    elif candidates:
        confidence = "possible_instance_created"
        warnings.append("new billable instance candidate appeared after launch request")
    elif disappeared:
        confidence = "uncertain"
        warnings.append("instance disappeared before ownership was recorded")
    elif billable:
        confidence = "uncertain"
        warnings.append("billable instance visible during incident diff")
    else:
        confidence = "likely_no_instance_created"
    if unmanaged:
        warnings.append("unmanaged billable instance requires manual review")
    return LambdaM029DiscoveryDiffReport(
        pre_instance_count=len(pre_instances),
        post_instance_count=len(post_instances),
        later_instance_count=None if later_instances is None else len(later_instances),
        new_instances_detected=new_instances,
        disappeared_instances=disappeared,
        billable_state_instances=billable,
        unmanaged_instances=unmanaged,
        possible_owned_candidates=candidates,
        confidence=confidence,
        warnings=warnings,
    )


def build_lambda_m029_discovery_diff_from_paths(
    *,
    pre_discovery: str | Path,
    post_discovery: str | Path,
    ledger: str | Path,
    later_discovery: str | Path | None = None,
) -> LambdaM029DiscoveryDiffReport:
    return build_lambda_m029_discovery_diff(
        pre_discovery=_load_json(pre_discovery),
        post_discovery=_load_json(post_discovery),
        later_discovery=None if later_discovery is None else _load_json(later_discovery),
        ledger=LambdaM029LaunchLedger.model_validate_json(
            Path(ledger).read_text(encoding="utf-8")
        ),
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


def load_lambda_m029_discovery_diff(path: str | Path) -> LambdaM029DiscoveryDiffReport:
    return LambdaM029DiscoveryDiffReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m029_discovery_diff(
    path: str | Path,
    report: LambdaM029DiscoveryDiffReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
