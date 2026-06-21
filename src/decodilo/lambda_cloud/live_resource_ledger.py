"""Ledger reconciliation for live read-only Lambda discovery reports."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan, load_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)


class LambdaLiveResourceLedgerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    discovered_count: int
    planned_count: int
    matched_count: int
    unmanaged_count: int
    unmanaged_instance_ids: list[str] = Field(default_factory=list)
    running_count: int = 0
    stopped_count: int = 0
    terminated_count: int = 0
    pending_count: int = 0
    unknown_count: int = 0
    billable_state_count: int = 0
    manual_review_required: bool = False
    advisory_actions: list[str] = Field(default_factory=list)
    live_api_used: bool
    no_mutations_performed: bool = True
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_lambda_live_resources(
    *,
    discovery: LambdaLiveDiscoveryReport,
    launch_plan: LambdaLaunchPlan,
) -> LambdaLiveResourceLedgerReport:
    planned_ids = {node.node_id for node in launch_plan.nodes}
    discovered_ids = {instance.instance_id for instance in discovery.instances}
    unmanaged = [
        instance.instance_id
        for instance in discovery.instances
        if not instance.tags.get("decodilo_run_id")
    ]
    state_counts = _state_counts(discovery.instances)
    advisories = []
    if unmanaged:
        advisories.append("manual review required for unmanaged Lambda instances")
    return LambdaLiveResourceLedgerReport(
        run_id=launch_plan.run_id,
        discovered_count=len(discovered_ids),
        planned_count=len(planned_ids),
        matched_count=len(planned_ids.intersection(discovered_ids)),
        unmanaged_count=len(unmanaged),
        unmanaged_instance_ids=unmanaged,
        running_count=state_counts["running"],
        stopped_count=state_counts["stopped"],
        terminated_count=state_counts["terminated"],
        pending_count=state_counts["pending"],
        unknown_count=state_counts["unknown"],
        billable_state_count=state_counts["billable"],
        manual_review_required=bool(unmanaged and state_counts["billable"] > 0),
        advisory_actions=advisories,
        live_api_used=discovery.live_api_used,
        warnings=["ledger is read-only and advisory; no mutation is performed"],
    )


def _state_counts(instances) -> dict[str, int]:  # noqa: ANN001
    counts = {"running": 0, "stopped": 0, "terminated": 0, "pending": 0, "unknown": 0}
    for instance in instances:
        status = str(getattr(instance, "status", "unknown")).lower()
        if status in {"active", "running"}:
            counts["running"] += 1
        elif status == "stopped":
            counts["stopped"] += 1
        elif status in {"terminated", "terminating"}:
            counts["terminated"] += 1
        elif status in {"pending", "booting"}:
            counts["pending"] += 1
        else:
            counts["unknown"] += 1
    counts["billable"] = counts["running"] + counts["pending"]
    return counts


def load_lambda_live_ledger_report(path: str | Path) -> LambdaLiveResourceLedgerReport:
    return LambdaLiveResourceLedgerReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_live_ledger_report(
    path: str | Path,
    report: LambdaLiveResourceLedgerReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def reconcile_lambda_live_resources_from_paths(
    *,
    discovery_report: str | Path,
    launch_plan: str | Path,
) -> LambdaLiveResourceLedgerReport:
    return reconcile_lambda_live_resources(
        discovery=load_lambda_live_discovery_report(discovery_report),
        launch_plan=load_lambda_launch_plan(launch_plan),
    )
