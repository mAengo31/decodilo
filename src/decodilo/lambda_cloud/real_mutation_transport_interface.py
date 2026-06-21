"""Interface models for the disabled real Lambda mutation transport skeleton."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRealMutationTransportStatus = Literal["disabled", "review_only"]


class LambdaRealMutationTransportCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    skeleton_present: bool = True
    executable_transport_available: bool = False
    supports_launch_one_instance: bool = False
    supports_terminate_owned_instance: bool = False
    supports_restart_instance: bool = False
    supports_create_delete_resources: bool = False
    blocks_before_request_construction: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False


class LambdaRealMutationOperationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_name: str
    operation_kind: Literal["future_mutation"] = "future_mutation"
    idempotency_key: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    dry_run_plan_hash: str = Field(min_length=1)
    approval_manifest_hash: str = Field(min_length=1)
    budget_lock_hash: str = Field(min_length=1)
    resource_ledger_hash: str = Field(min_length=1)
    teardown_plan_hash: str = Field(min_length=1)
    kill_switch_plan_hash: str = Field(min_length=1)
    operation_spec_hash: str = Field(min_length=1)
    owned_resource_scope: str = Field(min_length=1)
    request_payload_redacted: dict[str, object] = Field(default_factory=dict)
    request_body_present: bool = False
    fake_only: bool = False
    real_request_allowed: bool = False
    created_at_utc: str | None = None

    @model_validator(mode="after")
    def _disabled_request(self) -> LambdaRealMutationOperationRequest:
        if self.real_request_allowed:
            raise ValueError("real mutation requests are not allowed in M024")
        if self.request_body_present:
            raise ValueError("M024 operation requests cannot contain executable request bodies")
        if not self.request_payload_redacted:
            raise ValueError("redacted request payload summary is required")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealMutationOperationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_name: str
    status: LambdaRealMutationTransportStatus = "disabled"
    blocked_before_request_construction: bool = True
    request_constructed: bool = False
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_execution(self) -> LambdaRealMutationOperationResult:
        if (
            self.request_constructed
            or self.real_lambda_api_used
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
        ):
            raise ValueError("M024 mutation operation result cannot indicate execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealMutationTransport(BaseModel):
    model_config = ConfigDict(frozen=True)

    transport_schema_version: int = 1
    transport_status: LambdaRealMutationTransportStatus = "disabled"
    capabilities: LambdaRealMutationTransportCapabilities = Field(
        default_factory=LambdaRealMutationTransportCapabilities
    )
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_lambda_real_mutation_operation_request(
    path: str | Path,
) -> LambdaRealMutationOperationRequest:
    return LambdaRealMutationOperationRequest.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
