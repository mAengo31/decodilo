"""Teardown planning models for dry-run cloud plans."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeardownPlan(BaseModel):
    """Informational teardown plan.

    Dry-run plans have no live resource IDs because no launch path exists.
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    run_id: str
    resources_planned: list[str] = Field(default_factory=list)
    max_runtime_hours: float = Field(gt=0)
    termination_strategy: str = "dry-run-only-no-live-resources"
    expected_teardown_steps: list[str] = Field(default_factory=list)
    required_identifiers: list[str] = Field(default_factory=list)
    has_live_resource_ids: bool = False
    live_resource_ids: list[str] = Field(default_factory=list)
    teardown_verified: bool = False
    notes: str = "No live resources exist in dry-run plans."

    @model_validator(mode="after")
    def _validate_dry_run_ids(self) -> TeardownPlan:
        if self.has_live_resource_ids or self.live_resource_ids:
            raise ValueError("dry-run teardown plans must not contain live resource IDs")
        return self


def build_dry_run_teardown_plan(
    *,
    provider: str,
    run_id: str,
    resources_planned: list[str],
    max_runtime_hours: float,
) -> TeardownPlan:
    return TeardownPlan(
        provider=provider,
        run_id=run_id,
        resources_planned=resources_planned,
        max_runtime_hours=max_runtime_hours,
        expected_teardown_steps=[
            "future launcher records live resource identifiers before launch",
            "future launcher terminates all live instances before max runtime",
            "future launcher verifies provider-side termination",
        ],
        required_identifiers=["provider_resource_id"],
    )
