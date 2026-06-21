"""Flake handling policy for local and CI pytest profiles."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FlakePolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    policy_status: str = "active"
    silent_ignore_allowed: bool = False
    quick_excludes_subprocess_heavy: bool = True
    subprocess_recovery_tests_excluded_from_quick: bool = True
    bounded_retry_requires_reporting: bool = True
    recovery_flake_resolution: str = "prefer_deterministic_event_window"
    known_subprocess_sensitive_tests: list[str] = Field(
        default_factory=lambda: [
            "tests/test_local_process_failure.py::test_local_recovery_after_kill",
        ]
    )
    allowed_resolutions: list[str] = Field(
        default_factory=lambda: [
            "make_test_deterministic",
            "mark_subprocess_heavy_or_integration",
            "bounded_retry_with_explicit_reporting",
        ]
    )
    disallowed_resolutions: list[str] = Field(
        default_factory=lambda: [
            "ignore_without_tracking",
            "hide_by_over_broad_deselection",
            "remove_from_full_suite",
        ]
    )
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> FlakePolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("flake policy cannot enable launch or mutation")
        if not self.bounded_retry_requires_reporting:
            raise ValueError("bounded subprocess retries must report attempts and failures")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_flake_policy_report() -> FlakePolicyReport:
    return FlakePolicyReport()


def write_flake_policy_report(path: str | Path, report: FlakePolicyReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
