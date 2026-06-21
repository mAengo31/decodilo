"""M029 idempotency records for first real launch attempt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaM029IdempotentOperation = Literal["launch_one_instance", "terminate_owned_instance"]


class LambdaM029IdempotencyKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    key_schema_version: int = 1
    operation: LambdaM029IdempotentOperation
    run_id: str = Field(min_length=1)
    plan_hash: str = Field(min_length=1)
    owned_resource_scope: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def _operation_scoped(self) -> LambdaM029IdempotencyKey:
        if self.operation not in self.idempotency_key:
            raise ValueError("M029 idempotency key must include operation scope")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM029IdempotencyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_key: LambdaM029IdempotencyKey
    terminate_key: LambdaM029IdempotencyKey
    duplicate_launch_policy: str = "reconcile_same_owned_instance_or_manual_review"
    duplicate_terminate_policy: str = "safe_owned_termination_verification"
    idempotency_passed: bool = True
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_m029_idempotency_key(
    *,
    operation: LambdaM029IdempotentOperation,
    run_id: str,
    plan_hash: str,
    owned_resource_scope: str,
) -> LambdaM029IdempotencyKey:
    material = "|".join([operation, run_id, plan_hash, owned_resource_scope])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return LambdaM029IdempotencyKey(
        operation=operation,
        run_id=run_id,
        plan_hash=plan_hash,
        owned_resource_scope=owned_resource_scope,
        idempotency_key=f"m029-{operation}-{digest}",
    )


def build_m029_idempotency_report(
    *,
    run_id: str,
    plan_hash: str,
    owned_resource_scope: str = "future-owned-instance-only",
) -> LambdaM029IdempotencyReport:
    return LambdaM029IdempotencyReport(
        launch_key=build_m029_idempotency_key(
            operation="launch_one_instance",
            run_id=run_id,
            plan_hash=plan_hash,
            owned_resource_scope=owned_resource_scope,
        ),
        terminate_key=build_m029_idempotency_key(
            operation="terminate_owned_instance",
            run_id=run_id,
            plan_hash=plan_hash,
            owned_resource_scope=owned_resource_scope,
        ),
    )


def load_lambda_m029_idempotency_report(path: str | Path) -> LambdaM029IdempotencyReport:
    return LambdaM029IdempotencyReport.model_validate_json(Path(path).read_text("utf-8"))


def write_lambda_m029_idempotency_report(
    path: str | Path,
    report: LambdaM029IdempotencyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
