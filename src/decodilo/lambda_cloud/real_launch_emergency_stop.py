"""M029 owned-only emergency stop helper."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_launch_journal import replay_m029_launch_journal
from decodilo.lambda_cloud.real_launch_ledger import (
    load_lambda_m029_launch_ledger,
    write_lambda_m029_launch_ledger,
)
from decodilo.lambda_cloud.real_terminate_client import LambdaM029RealTerminateClient
from decodilo.lambda_cloud.real_termination_executor import LambdaM029TerminationExecutor

CONFIRM_EMERGENCY_TERMINATE = "I understand this terminates only the owned instance"


class LambdaM029EmergencyStopReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    emergency_stop_attempted: bool
    owned_instance_id: str | None = None
    termination_verified: bool = False
    manual_review_required: bool = False
    terminate_unowned_forbidden: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_m029_emergency_stop(
    *,
    journal_path: str | Path,
    ledger_path: str | Path,
    terminate_client: LambdaM029RealTerminateClient,
    executor: LambdaM029TerminationExecutor,
    arming_token: LambdaM029ArmingToken,
    idempotency_key: str,
    confirm_terminate_required: str,
) -> LambdaM029EmergencyStopReport:
    blockers: list[str] = []
    if confirm_terminate_required != CONFIRM_EMERGENCY_TERMINATE:
        blockers.append("missing exact emergency terminate confirmation")
    replay = replay_m029_launch_journal(journal_path)
    ledger = load_lambda_m029_launch_ledger(ledger_path)
    owned_id = ledger.owned_instance_id or replay.owned_instance_id
    if not owned_id:
        blockers.append("owned instance id missing")
    if blockers:
        return LambdaM029EmergencyStopReport(
            emergency_stop_attempted=False,
            owned_instance_id=owned_id,
            blockers=blockers,
            manual_review_required=True,
        )
    assert owned_id is not None
    if not ledger.can_terminate(owned_id):
        blockers.append("ledger does not authorize owned termination")
        return LambdaM029EmergencyStopReport(
            emergency_stop_attempted=False,
            owned_instance_id=owned_id,
            blockers=blockers,
            manual_review_required=True,
        )
    del terminate_client
    result, updated = executor.terminate_owned_instance(
        owned_instance_id=owned_id,
        ledger=ledger,
        arming_token=arming_token,
        idempotency_key=idempotency_key,
    )
    write_lambda_m029_launch_ledger(ledger_path, updated)
    return LambdaM029EmergencyStopReport(
        emergency_stop_attempted=True,
        owned_instance_id=owned_id,
        termination_verified=result.termination_verified,
        manual_review_required=result.manual_review_required,
        warnings=["Emergency stop is scoped to the recorded owned instance only."],
    )


def write_lambda_m029_emergency_stop_report(
    path: str | Path,
    report: LambdaM029EmergencyStopReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
