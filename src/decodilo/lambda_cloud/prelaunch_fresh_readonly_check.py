"""Optional fresh read-only prelaunch check summary for M026."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LambdaPrelaunchFreshReadOnlyCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    fresh_readonly_refresh_run: bool = False
    source: str = "existing_m019c_evidence"
    live_api_used: bool = False
    read_operations: int = 0
    mutating_operations: int = 0
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def write_lambda_prelaunch_fresh_readonly_check(
    path: str | Path,
    report: LambdaPrelaunchFreshReadOnlyCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
