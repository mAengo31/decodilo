"""Fail-closed Lambda operation mutation guard."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

READ_ONLY_OPERATIONS: frozenset[str] = frozenset(
    {
        "list_instance_types",
        "list_regions",
        "list_images",
        "list_ssh_keys",
        "list_filesystems",
        "list_instances",
        "get_instance",
        "get_quota",
        "get_usage_estimate",
    }
)

MUTATING_OPERATIONS: frozenset[str] = frozenset(
    {
        "launch_instance",
        "terminate_instance",
        "restart_instance",
        "create_ssh_key",
        "delete_ssh_key",
        "create_filesystem",
        "delete_filesystem",
    }
)

M029_MUTATING_OPERATIONS: frozenset[str] = frozenset(
    {
        "launch_one_instance",
        "terminate_owned_instance",
    }
)


class LambdaOperation(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    operation_type: Literal["read", "mutate", "unknown"]


class LambdaMutationGuardReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    allowed: bool
    reason: str
    operation_type: Literal["read", "mutate", "unknown"]
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMutationGuard:
    """Allow only known read operations; deny mutations and unknowns."""

    def check(self, operation: str) -> LambdaMutationGuardReport:
        if operation in READ_ONLY_OPERATIONS:
            return LambdaMutationGuardReport(
                operation=operation,
                allowed=True,
                reason="read-only operation allowlisted",
                operation_type="read",
            )
        if operation in MUTATING_OPERATIONS:
            return LambdaMutationGuardReport(
                operation=operation,
                allowed=False,
                reason="mutating Lambda operations are disabled",
                operation_type="mutate",
            )
        return LambdaMutationGuardReport(
            operation=operation,
            allowed=False,
            reason="unknown Lambda operation denied by default",
            operation_type="unknown",
        )

    def check_m029(self, operation: str, *, armed: bool) -> LambdaMutationGuardReport:
        if operation in READ_ONLY_OPERATIONS:
            return self.check(operation)
        if operation in M029_MUTATING_OPERATIONS:
            return LambdaMutationGuardReport(
                operation=operation,
                allowed=armed,
                reason=(
                    "M029 armed operation allowlisted"
                    if armed
                    else "M029 mutation requires arming token"
                ),
                operation_type="mutate",
            )
        return self.check(operation)
