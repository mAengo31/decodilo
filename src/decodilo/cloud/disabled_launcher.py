"""Disabled launcher implementation for the dry-run-only scaffold."""

from __future__ import annotations

from decodilo.cloud.launcher_interface import LaunchRequest, LaunchResult
from decodilo.cloud.teardown_plan import TeardownPlan
from decodilo.errors import LaunchDisabledError


class DisabledCloudLauncher:
    """A launcher that proves cloud launch paths remain unavailable."""

    def launch(self, request: LaunchRequest) -> LaunchResult:
        raise LaunchDisabledError(
            f"cloud launch is disabled for run {request.plan.run_id}; "
            "the current scaffold only permits dry-run planning"
        )

    def teardown(self, plan: TeardownPlan) -> LaunchResult:
        raise LaunchDisabledError(
            f"cloud teardown is disabled for run {plan.run_id}; no live resources exist"
        )
