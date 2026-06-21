"""Feature flags for the disabled Lambda real mutation skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaMutationFeatureFlags(BaseModel):
    model_config = ConfigDict(frozen=True)

    real_mutation_feature_present: bool = True
    real_mutation_transport_executable: bool = False
    launch_execution_enabled: bool = False
    termination_execution_enabled: bool = False
    mutation_arming_allowed: bool = False
    environment_can_enable: bool = False
    cli_can_enable: bool = False
    config_can_enable: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reject_enabled_flags(self) -> LambdaMutationFeatureFlags:
        enabled = [
            name
            for name in [
                "real_mutation_transport_executable",
                "launch_execution_enabled",
                "termination_execution_enabled",
                "mutation_arming_allowed",
                "environment_can_enable",
                "cli_can_enable",
                "config_can_enable",
            ]
            if getattr(self, name)
        ]
        if enabled:
            raise ValueError(f"M024 cannot enable mutation feature flags: {', '.join(enabled)}")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMutationFeatureFlagReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    flags: LambdaMutationFeatureFlags
    feature_flag_status: str = "disabled"
    environment_override_attempted: bool = False
    cli_override_attempted: bool = False
    config_override_attempted: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def default_lambda_mutation_feature_flags() -> LambdaMutationFeatureFlags:
    return LambdaMutationFeatureFlags(
        warnings=["Skeleton feature is present, but execution flags are disabled."]
    )


def evaluate_lambda_mutation_feature_flags(
    flags: LambdaMutationFeatureFlags | None = None,
) -> LambdaMutationFeatureFlagReport:
    effective = flags or default_lambda_mutation_feature_flags()
    return LambdaMutationFeatureFlagReport(
        flags=effective,
        warnings=["Environment, CLI, and config cannot enable mutation in M024."],
    )


def load_lambda_mutation_feature_flags(path: str | Path) -> LambdaMutationFeatureFlags:
    return LambdaMutationFeatureFlags.model_validate_json(Path(path).read_text(encoding="utf-8"))
