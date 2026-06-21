"""M027 fake-server-only minimal mutation execution context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaMinimalMutationExecutionMode = Literal[
    "disabled",
    "fake_server_only",
    "real_lambda_forbidden",
]

_REAL_LAMBDA_MARKERS = (
    "cloud.lambdalabs.com",
    "lambda.ai",
    "lambdalabs.com",
)
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


class LambdaMinimalMutationExecutionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_schema_version: int = 1
    mode: LambdaMinimalMutationExecutionMode = "disabled"
    base_url: str | None = None
    fake_server_mode: bool = False
    run_id: str = Field(min_length=1)
    m027_authorization_hash: str = Field(min_length=1)
    operation_spec_hash: str = Field(min_length=1)
    approval_manifest_hash: str = Field(min_length=1)
    budget_lock_hash: str = Field(min_length=1)
    idempotency_plan_hash: str = Field(min_length=1)
    resource_scope_hash: str = Field(min_length=1)
    teardown_plan_hash: str = Field(min_length=1)
    kill_switch_plan_hash: str | None = None
    endpoint_policy_enabled: bool = True
    mutation_guard_enabled: bool = True
    credential_source: str | None = None
    real_lambda_base_url_allowed: bool = False
    real_lambda_credentials_allowed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_context(self) -> LambdaMinimalMutationExecutionContext:
        if (
            self.real_lambda_base_url_allowed
            or self.real_lambda_credentials_allowed
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
        ):
            raise ValueError("M027 context cannot enable real Lambda execution")
        if self.credential_source:
            raise ValueError("M027 minimal mutation context must not include credentials")
        if self.base_url and _is_real_lambda_url(self.base_url):
            raise ValueError("M027 minimal mutation rejects real Lambda base URLs")
        if self.mode == "fake_server_only":
            if not self.fake_server_mode:
                raise ValueError("fake_server_only mode requires fake_server_mode=true")
            if self.base_url and not _is_local_url(self.base_url):
                raise ValueError("fake_server_only mode requires localhost or in-memory URL")
        else:
            if self.fake_server_mode:
                raise ValueError("fake_server_mode requires mode=fake_server_only")
        return self

    @property
    def fake_execution_candidate(self) -> bool:
        return self.mode == "fake_server_only" and self.fake_server_mode

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_fake_server_execution_context(
    *,
    run_id: str = "lambda-minimal-mutation-m027",
    base_url: str | None = "memory://lambda-minimal-fake-server",
    m027_authorization_hash: str = "m027-authorization-hash",
    operation_spec_hash: str = "operation-spec-hash",
    approval_manifest_hash: str = "approval-hash",
    budget_lock_hash: str = "budget-lock-hash",
    idempotency_plan_hash: str = "idempotency-plan-hash",
    resource_scope_hash: str = "resource-scope-hash",
    teardown_plan_hash: str = "teardown-plan-hash",
    kill_switch_plan_hash: str | None = "kill-switch-plan-hash",
) -> LambdaMinimalMutationExecutionContext:
    return LambdaMinimalMutationExecutionContext(
        mode="fake_server_only",
        base_url=base_url,
        fake_server_mode=True,
        run_id=run_id,
        m027_authorization_hash=m027_authorization_hash,
        operation_spec_hash=operation_spec_hash,
        approval_manifest_hash=approval_manifest_hash,
        budget_lock_hash=budget_lock_hash,
        idempotency_plan_hash=idempotency_plan_hash,
        resource_scope_hash=resource_scope_hash,
        teardown_plan_hash=teardown_plan_hash,
        kill_switch_plan_hash=kill_switch_plan_hash,
    )


def _is_real_lambda_url(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _REAL_LAMBDA_MARKERS)


def _is_local_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme == "memory":
        return True
    return parsed.hostname in _LOCAL_HOSTS


def load_lambda_minimal_mutation_execution_context(
    path: str | Path,
) -> LambdaMinimalMutationExecutionContext:
    return LambdaMinimalMutationExecutionContext.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_minimal_mutation_execution_context(
    path: str | Path,
    context: LambdaMinimalMutationExecutionContext,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(context.to_json(), encoding="utf-8")
