"""Cloud launcher protocol definitions.

The interface is intentionally present before any implementation so future launch
work has an auditable boundary. The current scaffold ships only a disabled
launcher.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.teardown_plan import TeardownPlan


class LaunchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: CloudLaunchPlan
    operator_acknowledged: bool = False


class LaunchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    launched: bool = False
    disabled: bool = True
    provider: str
    run_id: str
    message: str
    resource_ids: list[str] = Field(default_factory=list)


class CloudLauncher(Protocol):
    def launch(self, request: LaunchRequest) -> LaunchResult:
        """Launch resources for a reviewed plan."""

    def teardown(self, plan: TeardownPlan) -> LaunchResult:
        """Tear down resources created by a launch."""
