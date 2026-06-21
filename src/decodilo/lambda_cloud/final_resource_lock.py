"""M028 final Lambda resource lock."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_plan import load_lambda_launch_plan
from decodilo.lambda_cloud.m020_report import LambdaM020ReadinessReport, load_lambda_m020_report


class LambdaFinalResourceLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    lock_id: str = "lambda-final-resource-lock-m028"
    m020_report_ref: str
    planned_region: str
    planned_instance_type: str
    planned_gpu_type: str
    planned_gpus_per_instance: int
    image_ref: str | None = None
    ssh_key_ref: str | None = None
    filesystem_refs: list[str] = Field(default_factory=list)
    terminate_scope: str = "future_owned_instance_only"
    unmanaged_billable_count: int = 0
    selected_price_record_id: str | None = None
    lock_hash: str
    resource_lock_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalResourceLock:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 resource lock cannot enable launch or mutation")
        if self.terminate_scope != "future_owned_instance_only":
            raise ValueError("termination scope must be future owned resource only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaFinalResourceLockReport = LambdaFinalResourceLock


def build_lambda_final_resource_lock(
    m020_report: str | Path | LambdaM020ReadinessReport,
) -> LambdaFinalResourceLock:
    report = (
        m020_report
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else load_lambda_m020_report(m020_report)
    )
    plan = load_lambda_launch_plan(report.launch_plan_ref)
    price = report.price_reconciliation
    resources = report.resource_reconciliation
    blockers: list[str] = []
    if not resources.region_matches:
        blockers.append("planned region missing from discovery")
    if resources.unmanaged_billable_instances:
        blockers.append("unmanaged billable resources present")
    if not resources.resource_reconciliation_passed:
        blockers.append("resource reconciliation did not pass")
    if price.selected_price_record_id is None:
        blockers.append("selected price record missing")
    material = "|".join(
        [
            plan.region,
            plan.instance_type,
            price.selected_gpu_type,
            str(price.selected_gpus_per_instance),
            str(price.selected_price_record_id),
        ]
    )
    report_ref = (
        "<in-memory>"
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else str(m020_report)
    )
    return LambdaFinalResourceLock(
        m020_report_ref=report_ref,
        planned_region=plan.region,
        planned_instance_type=plan.instance_type,
        planned_gpu_type=price.selected_gpu_type,
        planned_gpus_per_instance=price.selected_gpus_per_instance,
        image_ref=plan.image,
        ssh_key_ref=plan.ssh_key_ref,
        filesystem_refs=plan.filesystem_refs,
        unmanaged_billable_count=resources.unmanaged_billable_instances,
        selected_price_record_id=price.selected_price_record_id,
        lock_hash=hashlib.sha256(material.encode("utf-8")).hexdigest(),
        resource_lock_passed=not blockers,
        blockers=blockers,
        warnings=["Final resource lock is review evidence only and creates no resources."],
    )


def load_lambda_final_resource_lock(path: str | Path) -> LambdaFinalResourceLock:
    return LambdaFinalResourceLock.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_final_resource_lock(path: str | Path, lock: LambdaFinalResourceLock) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(lock.to_json(), encoding="utf-8")
