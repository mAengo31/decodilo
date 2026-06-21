"""Deterministic fake Lambda lifecycle failure injection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FakeLambdaFailureMode = Literal[
    "none",
    "fail_before_launch_commit",
    "fail_after_launch_before_health",
    "health_check_timeout",
    "terminate_timeout",
    "partial_terminate_failure",
    "journal_write_failure",
    "duplicate_launch_request",
    "duplicate_teardown_request",
    "process_crash_after_fake_launch",
]


class FakeLambdaFailureConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    failure_mode: FakeLambdaFailureMode = "none"
    seed: int = 0
    fail_resource_index: int = Field(default=0, ge=0)

    def enabled(self, mode: FakeLambdaFailureMode) -> bool:
        return self.failure_mode == mode

