"""Non-executable Lambda termination and verification runbook for M025."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaTerminationRunbookStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    description: str
    non_executable: bool = True


class LambdaTerminationRunbook(BaseModel):
    model_config = ConfigDict(frozen=True)

    runbook_schema_version: int = 1
    runbook_id: str = "lambda-termination-runbook-m025"
    owned_instance_id_source: str
    steps: list[LambdaTerminationRunbookStep]
    terminal_states: list[str] = Field(default_factory=lambda: ["terminated", "absent"])
    os_shutdown_insufficient_statement: str
    executable_terminate_command_present: bool = False
    manual_review_triggers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _review_only(self) -> LambdaTerminationRunbook:
        if not self.owned_instance_id_source:
            raise ValueError("termination runbook requires owned instance id source")
        if self.executable_terminate_command_present:
            raise ValueError(
                "M025 termination runbook cannot contain executable terminate commands"
            )
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M025 termination runbook cannot enable launch")
        if any(not step.non_executable for step in self.steps):
            raise ValueError("all termination runbook steps must be non-executable")
        if "OS shutdown is insufficient" not in self.os_shutdown_insufficient_statement:
            raise ValueError("termination runbook must state OS shutdown is insufficient")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_termination_runbook() -> LambdaTerminationRunbook:
    return LambdaTerminationRunbook(
        owned_instance_id_source="future launch ledger owned_resource_scope",
        steps=[
            LambdaTerminationRunbookStep(
                step_id="owned_id",
                description="Read owned instance ID from the future launch ledger.",
            ),
            LambdaTerminationRunbookStep(
                step_id="terminate_only_owned",
                description="Future termination may target only the owned instance ID.",
            ),
            LambdaTerminationRunbookStep(
                step_id="read_only_verify",
                description="Use read-only list/get verification until absent or terminal.",
            ),
            LambdaTerminationRunbookStep(
                step_id="timeout",
                description="On timeout, stop and require manual review.",
            ),
            LambdaTerminationRunbookStep(
                step_id="malformed_response",
                description="On malformed response, preserve evidence and require manual review.",
            ),
            LambdaTerminationRunbookStep(
                step_id="ledger_reconcile",
                description="Reconcile resource ledger and collect audit artifacts.",
            ),
        ],
        os_shutdown_insufficient_statement=(
            "OS shutdown is insufficient; Lambda resource termination must be verified "
            "through read-only provider state."
        ),
        manual_review_triggers=[
            "unknown state",
            "list/get unavailable",
            "timeout",
            "ledger mismatch",
        ],
        warnings=["Termination runbook is non-executable in M025."],
    )


def load_lambda_termination_runbook(path: str | Path) -> LambdaTerminationRunbook:
    return LambdaTerminationRunbook.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_termination_runbook(
    path: str | Path,
    runbook: LambdaTerminationRunbook,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(runbook.to_json(), encoding="utf-8")
