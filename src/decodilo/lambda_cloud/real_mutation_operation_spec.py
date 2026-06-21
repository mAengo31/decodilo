"""Review-only Lambda real mutation operation specification for M023."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRealMutationOperationStatus = Literal["specified", "excluded", "already_read_only"]


class LambdaRealMutationOperationSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_name: str
    future_http_method: str | None = None
    future_endpoint_template: str | None = None
    operation_kind: Literal["read", "future_mutation"]
    operation_status: LambdaRealMutationOperationStatus = "specified"
    allowed_in_m023: bool = False
    requires_idempotency_key: bool = False
    requires_budget_gate: bool = False
    requires_approval_gate: bool = False
    requires_resource_ledger: bool = False
    requires_teardown_plan: bool = False
    requires_termination_verification: bool = False
    allowed_resource_scope: str = "none"
    forbidden_resource_scope: str = "all real resources"
    failure_modes: list[str] = Field(default_factory=list)
    audit_events_required: list[str] = Field(default_factory=list)
    rollback_or_teardown_required: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _no_future_mutation_allowed(self) -> LambdaRealMutationOperationSpec:
        if self.operation_kind == "future_mutation" and self.allowed_in_m023:
            raise ValueError("future mutation operations are not allowed in M023")
        return self


class LambdaRealMutationOperationSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operations: list[LambdaRealMutationOperationSpec]
    explicitly_excluded: list[str]
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_disabled_flags(self) -> LambdaRealMutationOperationSet:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 operation spec cannot enable real mutation or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_real_mutation_operation_set() -> LambdaRealMutationOperationSet:
    future_common = {
        "operation_kind": "future_mutation",
        "requires_idempotency_key": True,
        "requires_budget_gate": True,
        "requires_approval_gate": True,
        "requires_resource_ledger": True,
        "requires_teardown_plan": True,
        "requires_termination_verification": True,
        "allowed_resource_scope": "single ledger-owned first-launch resource",
        "forbidden_resource_scope": "unowned resources, multi-node launches, background work",
        "audit_events_required": [
            "arming_gate_checked",
            "budget_gate_checked",
            "approval_hash_checked",
            "resource_ledger_checked",
            "mutation_attempt_recorded",
        ],
        "rollback_or_teardown_required": True,
    }
    operations = [
        LambdaRealMutationOperationSpec(
            operation_name="launch_one_instance",
            future_http_method="POST",
            future_endpoint_template="/instance-operations/launch",
            failure_modes=[
                "launch request succeeds but response lost",
                "launch request times out but instance exists",
                "duplicate launch request",
            ],
            notes="Spec only; no POST transport exists in M023.",
            **future_common,
        ),
        LambdaRealMutationOperationSpec(
            operation_name="list_instances_read_only",
            future_http_method="GET",
            future_endpoint_template="/instances",
            operation_kind="read",
            operation_status="already_read_only",
            allowed_in_m023=True,
            allowed_resource_scope="read-only account inventory",
            forbidden_resource_scope="mutation",
            failure_modes=["list endpoint unavailable during verification"],
            audit_events_required=["read_only_request_recorded"],
            notes="Already implemented through live read-only discovery.",
        ),
        LambdaRealMutationOperationSpec(
            operation_name="get_instance_read_only",
            future_http_method="GET",
            future_endpoint_template="/instances/{instance_id}",
            operation_kind="read",
            operation_status="already_read_only",
            allowed_in_m023=True,
            allowed_resource_scope="read-only lookup by recorded instance id",
            forbidden_resource_scope="mutation",
            failure_modes=["get endpoint unavailable during verification"],
            audit_events_required=["read_only_request_recorded"],
            notes="Already implemented through live read-only discovery.",
        ),
        LambdaRealMutationOperationSpec(
            operation_name="terminate_owned_instance",
            future_http_method="POST",
            future_endpoint_template="/instance-operations/terminate",
            failure_modes=[
                "terminate request succeeds but response lost",
                "terminate request times out",
                "duplicate terminate request",
            ],
            notes="Spec only; must be restricted to ledger-owned instance id.",
            **future_common,
        ),
        LambdaRealMutationOperationSpec(
            operation_name="verify_terminated_read_only",
            future_http_method="GET",
            future_endpoint_template="/instances/{instance_id}",
            operation_kind="read",
            operation_status="already_read_only",
            allowed_in_m023=True,
            requires_resource_ledger=True,
            requires_termination_verification=True,
            allowed_resource_scope="read-only terminal-state verification",
            forbidden_resource_scope="termination mutation",
            failure_modes=["termination state unknown"],
            audit_events_required=["read_only_verification_recorded"],
            notes="Read-only verification step for future termination policy.",
        ),
    ]
    excluded = [
        "restart_instance",
        "create_ssh_key",
        "delete_ssh_key",
        "create_filesystem",
        "delete_filesystem",
        "launch_multiple_instances",
        "launch_without_teardown_plan",
        "launch_without_budget_manifest",
        "launch_without_idempotency_key",
        "launch_without_resource_ledger",
        "launch_without_human_approval",
        "terminate_unowned_instance",
        "terminate_without_ledger_match",
    ]
    return LambdaRealMutationOperationSet(
        operations=operations,
        explicitly_excluded=excluded,
        warnings=["M023 is review-only; future mutation operations remain disabled."],
    )


def load_lambda_real_mutation_operation_set(path: str | Path) -> LambdaRealMutationOperationSet:
    return LambdaRealMutationOperationSet.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_operation_set(
    path: str | Path,
    operation_set: LambdaRealMutationOperationSet,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(operation_set.to_json(), encoding="utf-8")
