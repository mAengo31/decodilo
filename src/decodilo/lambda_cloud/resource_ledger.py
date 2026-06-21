"""Local Lambda resource ledger for planned and fake-discovered resources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.discovery import LambdaDiscoveryReport

LambdaResourceState = Literal[
    "planned",
    "discovered",
    "launched_future_only",
    "terminated_future_only",
    "unmanaged",
    "orphan_candidate",
    "unknown",
]


class LambdaResourceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_id: str
    resource_type: str
    state: LambdaResourceState
    ownership: str | None = None
    cost_attribution: dict[str, str] = Field(default_factory=dict)
    teardown_status: str = "not_applicable_m018"
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class LambdaResourceLedger(BaseModel):
    model_config = ConfigDict(frozen=True)

    ledger_schema_version: int = 1
    run_id: str
    planned_resources: list[LambdaResourceRecord] = Field(default_factory=list)
    discovered_resources: list[LambdaResourceRecord] = Field(default_factory=list)
    orphan_candidates: list[str] = Field(default_factory=list)
    live_api_used: bool = False
    launch_performed: bool = False
    terminate_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaLedgerReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    ledger: LambdaResourceLedger
    planned_count: int
    discovered_count: int
    unmanaged_count: int
    orphan_candidates: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_resource_ledger(
    *,
    run_id: str,
    planned_node_ids: list[str],
    discovery: LambdaDiscoveryReport,
) -> LambdaLedgerReconciliationReport:
    planned = [
        LambdaResourceRecord(
            resource_id=node_id,
            resource_type="lambda_instance",
            state="planned",
            ownership=run_id,
            cost_attribution={"run_id": run_id},
        )
        for node_id in planned_node_ids
    ]
    discovered: list[LambdaResourceRecord] = []
    orphan_candidates: list[str] = []
    for instance in discovery.running_instances:
        ownership = instance.tags.get("decodilo_run_id") if instance.tags else None
        state: LambdaResourceState = "discovered" if ownership else "orphan_candidate"
        if not ownership:
            orphan_candidates.append(instance.instance_id)
        discovered.append(
            LambdaResourceRecord(
                resource_id=instance.instance_id,
                resource_type="lambda_instance",
                state=state,
                ownership=ownership,
                cost_attribution={"hourly_cost": str(instance.hourly_cost or 0)},
                metadata={"status": instance.status, "region_id": instance.region_id},
            )
        )
    ledger = LambdaResourceLedger(
        run_id=run_id,
        planned_resources=planned,
        discovered_resources=discovered,
        orphan_candidates=orphan_candidates,
    )
    return LambdaLedgerReconciliationReport(
        passed=True,
        ledger=ledger,
        planned_count=len(planned),
        discovered_count=len(discovered),
        unmanaged_count=len(orphan_candidates),
        orphan_candidates=orphan_candidates,
        warnings=[
            "ledger reconciliation used fake discovery only; no live Lambda resources changed"
        ],
    )


def load_lambda_ledger_report(path: str | Path) -> LambdaLedgerReconciliationReport:
    return LambdaLedgerReconciliationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ledger_report(path: str | Path, report: LambdaLedgerReconciliationReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
