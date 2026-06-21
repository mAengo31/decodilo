"""M028 final decision record for future M029 launch attempt authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.final_no_mutation_audit import (
    LambdaFinalNoMutationAudit,
    load_lambda_final_no_mutation_audit,
)
from decodilo.lambda_cloud.final_prelaunch_state_snapshot import (
    LambdaFinalPrelaunchStateSnapshot,
    load_lambda_final_prelaunch_state_snapshot,
)
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)

LambdaM028DecisionStatus = Literal[
    "blocked",
    "needs_more_evidence",
    "authorized_for_m029_one_instance_launch_attempt",
]


class LambdaM028DecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_id: str = "lambda-m028-decision-record"
    status: LambdaM028DecisionStatus
    m029_authorization_ref: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaM028DecisionRecord:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 decision cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m028_decision_record(
    *,
    m029_authorization: str | Path | LambdaM029AuthorizationPackage,
    state_snapshot: str | Path | LambdaFinalPrelaunchStateSnapshot | None = None,
    no_mutation_audit: str | Path | LambdaFinalNoMutationAudit | None = None,
) -> LambdaM028DecisionRecord:
    package, ref = _load_package(m029_authorization)
    snapshot = _load_snapshot(state_snapshot)
    audit = _load_audit(no_mutation_audit)
    blockers = [*package.blockers]
    if snapshot is None:
        blockers.append("final state snapshot missing")
    elif not snapshot.snapshot_passed:
        blockers.extend(snapshot.blockers)
    if audit is None:
        blockers.append("final no-mutation audit missing")
    elif not audit.audit_passed:
        blockers.extend(audit.blockers)
    if not package.package_passed:
        blockers.append("M029 authorization package did not pass")
    if blockers:
        status: LambdaM028DecisionStatus = "needs_more_evidence"
        if audit is not None and not audit.audit_passed:
            status = "blocked"
    else:
        status = "authorized_for_m029_one_instance_launch_attempt"
    return LambdaM028DecisionRecord(
        status=status,
        m029_authorization_ref=ref,
        blockers=blockers,
        warnings=["M028 decision authorizes M029 attempt only; M028 cannot launch."],
    )


def _load_package(
    value: str | Path | LambdaM029AuthorizationPackage,
) -> tuple[LambdaM029AuthorizationPackage, str]:
    if isinstance(value, LambdaM029AuthorizationPackage):
        return value, "<in-memory>"
    return load_lambda_m029_authorization_package(value), str(value)


def _load_snapshot(
    value: str | Path | LambdaFinalPrelaunchStateSnapshot | None,
) -> LambdaFinalPrelaunchStateSnapshot | None:
    if value is None or isinstance(value, LambdaFinalPrelaunchStateSnapshot):
        return value
    return load_lambda_final_prelaunch_state_snapshot(value)


def _load_audit(
    value: str | Path | LambdaFinalNoMutationAudit | None,
) -> LambdaFinalNoMutationAudit | None:
    if value is None or isinstance(value, LambdaFinalNoMutationAudit):
        return value
    return load_lambda_final_no_mutation_audit(value)


def load_lambda_m028_decision_record(path: str | Path) -> LambdaM028DecisionRecord:
    return LambdaM028DecisionRecord.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m028_decision_record(
    path: str | Path,
    record: LambdaM028DecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")

