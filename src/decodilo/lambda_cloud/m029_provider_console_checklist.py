"""Provider console checklist for M029 manual incident review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LambdaM029ProviderConsoleChecklist(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    checklist_id: str = "lambda-m029-provider-console-checklist"
    steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_provider_console_checklist() -> LambdaM029ProviderConsoleChecklist:
    return LambdaM029ProviderConsoleChecklist(
        steps=[
            "Open Lambda console Instances page.",
            "Check running instances.",
            "Check pending instances.",
            "Check alert/error instances.",
            "Check recently terminated instances if visible.",
            "Compare instance timestamps with the M029C launch attempt window.",
            "If an instance is attributable to the attempt and running/pending, "
            "terminate it through the console.",
            "Record manual console confirmation.",
            "Do not terminate unrelated instances.",
        ],
        warnings=[
            "Console review is manual evidence only and does not authorize a second launch."
        ],
    )


def write_lambda_m029_provider_console_checklist(
    path: str | Path,
    checklist: LambdaM029ProviderConsoleChecklist,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(checklist.to_json(), encoding="utf-8")
