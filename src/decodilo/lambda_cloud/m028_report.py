"""Combined M028 final M029 authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.final_budget_lock import LambdaFinalBudgetLock
from decodilo.lambda_cloud.final_fresh_readonly_refresh import (
    LambdaFinalFreshReadOnlyRefreshReport,
)
from decodilo.lambda_cloud.final_no_mutation_audit import LambdaFinalNoMutationAudit
from decodilo.lambda_cloud.final_operator_confirmation import LambdaFinalOperatorConfirmation
from decodilo.lambda_cloud.final_prelaunch_state_snapshot import LambdaFinalPrelaunchStateSnapshot
from decodilo.lambda_cloud.final_resource_lock import LambdaFinalResourceLock
from decodilo.lambda_cloud.final_teardown_verification_plan import (
    LambdaFinalTeardownVerificationPlan,
)
from decodilo.lambda_cloud.launch_window_lock import LambdaLaunchWindowLock
from decodilo.lambda_cloud.m028_decision_record import (
    LambdaM028DecisionRecord,
    load_lambda_m028_decision_record,
)
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)


class LambdaM028Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-m028-final-authorization-report"
    fresh_readonly_refresh: LambdaFinalFreshReadOnlyRefreshReport | None = None
    state_snapshot: LambdaFinalPrelaunchStateSnapshot | None = None
    budget_lock: LambdaFinalBudgetLock | None = None
    resource_lock: LambdaFinalResourceLock | None = None
    launch_window_lock: LambdaLaunchWindowLock | None = None
    teardown_verification_plan: LambdaFinalTeardownVerificationPlan | None = None
    operator_confirmation: LambdaFinalOperatorConfirmation | None = None
    m029_authorization: LambdaM029AuthorizationPackage
    final_no_mutation_audit: LambdaFinalNoMutationAudit | None = None
    decision_record: LambdaM028DecisionRecord
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaM028Report:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m028_report(
    *,
    decision_record: str | Path | LambdaM028DecisionRecord,
    m029_authorization: str | Path | LambdaM029AuthorizationPackage,
) -> LambdaM028Report:
    decision = (
        decision_record
        if isinstance(decision_record, LambdaM028DecisionRecord)
        else load_lambda_m028_decision_record(decision_record)
    )
    authorization = (
        m029_authorization
        if isinstance(m029_authorization, LambdaM029AuthorizationPackage)
        else load_lambda_m029_authorization_package(m029_authorization)
    )
    blockers = [*decision.blockers, *authorization.blockers]
    return LambdaM028Report(
        m029_authorization=authorization,
        decision_record=decision,
        report_passed=not blockers,
        blockers=blockers,
        warnings=[
            "M029 authorization only; M028 build remains non-launchable",
            *decision.warnings,
            *authorization.warnings,
        ],
    )


def load_lambda_m028_report(path: str | Path) -> LambdaM028Report:
    return LambdaM028Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m028_report(path: str | Path, report: LambdaM028Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

