"""Plan-only idempotency model for future Lambda mutation requests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaMutationIdempotencyKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    plan_hash: str = Field(min_length=1)
    owned_resource_scope: str = Field(min_length=1)
    key: str = Field(min_length=1)
    deterministic: bool = True


class LambdaMutationIdempotencyPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    idempotency_key: LambdaMutationIdempotencyKey
    duplicate_launch_behavior: str = (
        "same key must resolve to same owned instance or require read-only reconciliation"
    )
    duplicate_terminate_behavior: str = "same key is safe and terminal state remains success"
    plan_only: bool = True
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaMutationIdempotencyPlan:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("idempotency plan cannot enable Lambda mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMutationIdempotencyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan: LambdaMutationIdempotencyPlan
    status: Literal["valid", "invalid"] = "valid"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_mutation_idempotency_plan(
    *,
    run_id: str,
    operation: str,
    plan_hash: str,
    owned_resource_scope: str = "planned-owned-placeholder",
) -> LambdaMutationIdempotencyPlan:
    key_material = "|".join([run_id, operation, plan_hash, owned_resource_scope])
    key = "idem-" + hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:24]
    return LambdaMutationIdempotencyPlan(
        idempotency_key=LambdaMutationIdempotencyKey(
            run_id=run_id,
            operation=operation,
            plan_hash=plan_hash,
            owned_resource_scope=owned_resource_scope,
            key=key,
        )
    )


def load_lambda_mutation_idempotency_plan(path: str | Path) -> LambdaMutationIdempotencyPlan:
    return LambdaMutationIdempotencyPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_mutation_idempotency_plan(
    path: str | Path,
    plan: LambdaMutationIdempotencyPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
