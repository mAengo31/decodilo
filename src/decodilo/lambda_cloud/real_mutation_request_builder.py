"""Disabled real Lambda mutation request builder for review-only plans."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.mutation_budget_lock import (
    LambdaMutationBudgetLock,
    load_lambda_mutation_budget_lock,
)
from decodilo.lambda_cloud.mutation_idempotency_plan import (
    LambdaMutationIdempotencyPlan,
    load_lambda_mutation_idempotency_plan,
)
from decodilo.lambda_cloud.mutation_request_redaction import (
    redact_lambda_mutation_request_payload,
)
from decodilo.lambda_cloud.mutation_resource_scope import (
    LambdaMutationResourceScope,
    load_lambda_mutation_resource_scope,
)
from decodilo.lambda_cloud.real_mutation_operation_spec import (
    LambdaRealMutationOperationSet,
    LambdaRealMutationOperationSpec,
    load_lambda_real_mutation_operation_set,
)
from decodilo.lambda_cloud.real_mutation_transport_interface import (
    LambdaRealMutationOperationRequest,
)


class LambdaRealMutationRequestBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operation_name: str
    build_status: Literal["review_plan_built", "blocked"] = "blocked"
    endpoint_template_metadata: str | None = None
    method_metadata: str | None = None
    required_fields_checklist: dict[str, bool] = Field(default_factory=dict)
    payload_schema_summary: dict[str, object] = Field(default_factory=dict)
    redacted_request: LambdaRealMutationOperationRequest | None = None
    executable_url: str | None = None
    executable_method: str | None = None
    executable_body: dict[str, object] | None = None
    request_body_present: bool = False
    real_request_allowed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_executable_request(self) -> LambdaRealMutationRequestBuildResult:
        if (
            self.executable_url is not None
            or self.executable_method is not None
            or self.executable_body is not None
            or self.request_body_present
            or self.real_request_allowed
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
        ):
            raise ValueError("M024 request builder cannot emit executable requests")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealMutationRequestBuilder(BaseModel):
    model_config = ConfigDict(frozen=True)

    builder_schema_version: int = 1
    disabled_in_m024: bool = True

    def build_review_plan(
        self,
        *,
        operation_name: str,
        operation_spec: str | Path | LambdaRealMutationOperationSet,
        budget_lock: str | Path | LambdaMutationBudgetLock | None,
        idempotency_plan: str | Path | LambdaMutationIdempotencyPlan | None,
        resource_scope: str | Path | LambdaMutationResourceScope | None,
        approval_manifest_hash: str = "review-only-approval-hash",
        dry_run_plan_hash: str = "review-only-plan-hash",
        teardown_plan_hash: str = "review-only-teardown-hash",
        kill_switch_plan_hash: str = "review-only-kill-switch-hash",
        resource_ledger_hash: str = "review-only-ledger-hash",
    ) -> LambdaRealMutationRequestBuildResult:
        spec_set = _load_spec(operation_spec)
        spec = _find_operation(spec_set, operation_name)
        lock = _load_budget_lock(budget_lock)
        idempotency = _load_idempotency(idempotency_plan)
        scope = _load_scope(resource_scope)
        checklist = {
            "operation_spec": spec is not None,
            "idempotency_plan": idempotency is not None,
            "approval_hash": bool(approval_manifest_hash),
            "budget_lock": lock is not None,
            "resource_scope": scope is not None,
            "teardown_plan_hash": bool(teardown_plan_hash),
            "kill_switch_plan_hash": bool(kill_switch_plan_hash),
        }
        missing = [name for name, present in checklist.items() if not present]
        if spec is not None and spec.operation_kind != "future_mutation":
            missing.append("future_mutation_operation")
        if missing or spec is None or lock is None or idempotency is None or scope is None:
            return LambdaRealMutationRequestBuildResult(
                operation_name=operation_name,
                required_fields_checklist=checklist,
                errors=[f"missing evidence: {name}" for name in missing],
                warnings=["No executable request was built."],
            )
        payload_summary = {
            "operation_name": operation_name,
            "run_id": idempotency.idempotency_key.run_id,
            "owned_resource_scope": scope.owned_scope.scope_id,
            "idempotency_key": idempotency.idempotency_key.key,
            "budget_lock_hash": lock.lock_hash,
        }
        redaction = redact_lambda_mutation_request_payload(payload_summary)
        request = LambdaRealMutationOperationRequest(
            operation_name=operation_name,
            idempotency_key=idempotency.idempotency_key.key,
            run_id=idempotency.idempotency_key.run_id,
            dry_run_plan_hash=dry_run_plan_hash,
            approval_manifest_hash=approval_manifest_hash,
            budget_lock_hash=lock.lock_hash,
            resource_ledger_hash=resource_ledger_hash,
            teardown_plan_hash=teardown_plan_hash,
            kill_switch_plan_hash=kill_switch_plan_hash,
            operation_spec_hash=_hash_model(spec),
            owned_resource_scope=scope.owned_scope.scope_id,
            request_payload_redacted=redaction.redacted_payload,
        )
        return LambdaRealMutationRequestBuildResult(
            operation_name=operation_name,
            build_status="review_plan_built",
            endpoint_template_metadata=spec.future_endpoint_template,
            method_metadata=spec.future_http_method,
            required_fields_checklist=checklist,
            payload_schema_summary={
                "fields": sorted(payload_summary),
                "redacted_fields": redaction.redacted_fields,
                "contains_executable_body": False,
            },
            redacted_request=request,
            warnings=["Review-only request plan built; executable URL/body omitted."],
        )


def _load_spec(
    value: str | Path | LambdaRealMutationOperationSet,
) -> LambdaRealMutationOperationSet:
    if isinstance(value, LambdaRealMutationOperationSet):
        return value
    return load_lambda_real_mutation_operation_set(value)


def _load_budget_lock(
    value: str | Path | LambdaMutationBudgetLock | None,
) -> LambdaMutationBudgetLock | None:
    if value is None:
        return None
    if isinstance(value, LambdaMutationBudgetLock):
        return value
    return load_lambda_mutation_budget_lock(value)


def _load_idempotency(
    value: str | Path | LambdaMutationIdempotencyPlan | None,
) -> LambdaMutationIdempotencyPlan | None:
    if value is None:
        return None
    if isinstance(value, LambdaMutationIdempotencyPlan):
        return value
    return load_lambda_mutation_idempotency_plan(value)


def _load_scope(
    value: str | Path | LambdaMutationResourceScope | None,
) -> LambdaMutationResourceScope | None:
    if value is None:
        return None
    if isinstance(value, LambdaMutationResourceScope):
        return value
    return load_lambda_mutation_resource_scope(value)


def _find_operation(
    operation_set: LambdaRealMutationOperationSet,
    operation_name: str,
) -> LambdaRealMutationOperationSpec | None:
    for operation in operation_set.operations:
        if operation.operation_name == operation_name:
            return operation
    return None


def _hash_model(model: BaseModel) -> str:
    return hashlib.sha256(
        json.dumps(model.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def load_lambda_real_mutation_request_build_result(
    path: str | Path,
) -> LambdaRealMutationRequestBuildResult:
    return LambdaRealMutationRequestBuildResult.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_request_build_result(
    path: str | Path,
    result: LambdaRealMutationRequestBuildResult,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.to_json(), encoding="utf-8")
