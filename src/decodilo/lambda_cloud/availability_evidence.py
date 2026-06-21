"""Lambda live availability evidence classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.final_fresh_readonly_refresh import (
    LambdaFinalFreshReadOnlyRefreshReport,
)
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport

LambdaAvailabilityStatus = Literal[
    "available",
    "unavailable",
    "unknown",
    "endpoint_inconclusive",
    "unsupported_endpoint",
    "not_checked",
]


class LambdaAvailabilityEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    status: LambdaAvailabilityStatus
    live_api_used: bool = False
    instance_type_endpoint_attempted: bool = False
    instance_type_count: int | None = None
    endpoint_semantics_known: bool = False
    required_endpoint_success: bool | None = None
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_availability_evidence(
    report: LambdaLiveDiscoveryReport | LambdaFinalFreshReadOnlyRefreshReport | dict[str, Any],
    *,
    endpoint_semantics_known: bool = False,
) -> LambdaAvailabilityEvidence:
    payload = report if isinstance(report, dict) else report.model_dump(mode="json")
    live_api_used = bool(payload.get("live_api_used", False))
    required_success = payload.get("required_endpoint_success")
    endpoint_results = payload.get("endpoint_results") or []
    attempted = any(result.get("operation") == "list_instance_types" for result in endpoint_results)
    instance_types = payload.get("instance_types")
    count = len(instance_types) if isinstance(instance_types, list) else None
    warnings: list[str] = []
    limitations: list[str] = []
    status: LambdaAvailabilityStatus
    if not live_api_used:
        status = "not_checked"
        limitations.append("no live Lambda API availability evidence was collected")
    elif count is None:
        status = "endpoint_inconclusive"
        limitations.append("refresh summary does not include instance-type records")
    elif count > 0:
        status = "available" if endpoint_semantics_known else "unknown"
        if not endpoint_semantics_known:
            warnings.append("live instance-type endpoint semantics are not proven")
    elif count == 0 and endpoint_semantics_known:
        status = "unavailable"
    else:
        status = "endpoint_inconclusive"
        warnings.append("live instance-type endpoint returned zero records")
        limitations.append("zero instance types is not treated as proof of product absence")
    if not attempted and endpoint_results:
        status = "unsupported_endpoint"
        warnings.append("instance-type endpoint was not attempted")
    return LambdaAvailabilityEvidence(
        status=status,
        live_api_used=live_api_used,
        instance_type_endpoint_attempted=attempted or count is not None,
        instance_type_count=count,
        endpoint_semantics_known=endpoint_semantics_known,
        required_endpoint_success=required_success,
        limitations=limitations,
        warnings=warnings,
    )


def load_lambda_availability_evidence(path: str | Path) -> LambdaAvailabilityEvidence:
    return LambdaAvailabilityEvidence.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_availability_evidence(
    path: str | Path,
    evidence: LambdaAvailabilityEvidence,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(evidence.to_json(), encoding="utf-8")
