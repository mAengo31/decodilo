"""Fake-only Lambda health checks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FakeLambdaHealthCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_id: str
    status: Literal["passed", "failed", "timeout"]
    healthy: bool
    warnings: list[str] = Field(default_factory=list)


def run_fake_lambda_health_check(
    resource_id: str,
    *,
    mode: Literal["pass", "fail", "timeout"] = "pass",
) -> FakeLambdaHealthCheckResult:
    if mode == "pass":
        return FakeLambdaHealthCheckResult(resource_id=resource_id, status="passed", healthy=True)
    if mode == "fail":
        return FakeLambdaHealthCheckResult(
            resource_id=resource_id,
            status="failed",
            healthy=False,
            warnings=["fake health check failed"],
        )
    return FakeLambdaHealthCheckResult(
        resource_id=resource_id,
        status="timeout",
        healthy=False,
        warnings=["fake health check timed out"],
    )

