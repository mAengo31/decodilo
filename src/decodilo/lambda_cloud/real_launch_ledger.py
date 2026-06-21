"""M029 owned-resource ledger."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaM029LaunchLedger(BaseModel):
    model_config = ConfigDict(frozen=True)

    ledger_schema_version: int = 1
    run_id: str
    owned_instance_id: str | None = None
    launch_attempt_id: str | None = None
    terminate_attempt_id: str | None = None
    resource_state: str = "unknown"
    billable_window_start_utc: str | None = None
    billable_window_end_utc: str | None = None
    termination_verified: bool = False
    manual_review_required: bool = False
    unowned_termination_attempted: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _owned_only(self) -> LambdaM029LaunchLedger:
        if self.unowned_termination_attempted:
            raise ValueError("M029 ledger cannot include unowned termination attempt")
        return self

    def can_terminate(self, instance_id: str) -> bool:
        return bool(self.owned_instance_id and instance_id == self.owned_instance_id)

    def record_owned(self, instance_id: str, *, launch_attempt_id: str) -> LambdaM029LaunchLedger:
        return self.model_copy(
            update={
                "owned_instance_id": instance_id,
                "launch_attempt_id": launch_attempt_id,
                "resource_state": "running",
            }
        )

    def record_terminated(
        self,
        *,
        terminate_attempt_id: str,
        verified: bool,
    ) -> LambdaM029LaunchLedger:
        return self.model_copy(
            update={
                "terminate_attempt_id": terminate_attempt_id,
                "resource_state": "terminated" if verified else "unknown",
                "termination_verified": verified,
                "manual_review_required": not verified,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_lambda_m029_launch_ledger(path: str | Path) -> LambdaM029LaunchLedger:
    return LambdaM029LaunchLedger.model_validate_json(Path(path).read_text("utf-8"))


def write_lambda_m029_launch_ledger(path: str | Path, ledger: LambdaM029LaunchLedger) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ledger.to_json(), encoding="utf-8")
