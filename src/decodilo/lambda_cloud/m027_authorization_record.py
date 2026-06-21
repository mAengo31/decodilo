"""M027 implementation authorization record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.real_launch_decision_record import (
    LambdaRealLaunchDecisionRecord,
    load_lambda_real_launch_decision_record,
)

LambdaM027AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_to_implement_minimal_mutation_code_disabled_by_default",
]


class LambdaM027AuthorizationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    record_id: str = "lambda-m027-authorization-record"
    decision_record_ref: str
    authorized_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    status: LambdaM027AuthorizationStatus
    next_milestone: str = "M027"
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaM027AuthorizationRecord:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M027 authorization record cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m027_authorization_record(
    decision_record: str | Path | LambdaRealLaunchDecisionRecord,
) -> LambdaM027AuthorizationRecord:
    if isinstance(decision_record, LambdaRealLaunchDecisionRecord):
        record = decision_record
        ref = "<in-memory>"
    else:
        record = load_lambda_real_launch_decision_record(decision_record)
        ref = str(decision_record)
    authorized = record.status == "approve_m027_minimal_real_mutation_implementation"
    return LambdaM027AuthorizationRecord(
        decision_record_ref=ref,
        status=(
            "authorized_to_implement_minimal_mutation_code_disabled_by_default"
            if authorized
            else "not_authorized"
        ),
        authorized_scope=[
            "implement minimal launch_one_instance request code",
            "implement minimal terminate_owned_instance request code",
            "integrate endpoint policy",
            "integrate arming gate",
            "integrate budget lock",
            "integrate idempotency",
            "integrate resource ledger",
            "integrate termination verification",
            "test against fake server only",
        ]
        if authorized
        else [],
        forbidden_scope=[
            "real launch execution",
            "real terminate execution",
            "restart",
            "create/delete keys/filesystems",
            "multi-instance launch",
            "SSH",
            "setup scripts",
            "training",
        ],
    )


def load_lambda_m027_authorization_record(path: str | Path) -> LambdaM027AuthorizationRecord:
    return LambdaM027AuthorizationRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m027_authorization_record(
    path: str | Path,
    record: LambdaM027AuthorizationRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
