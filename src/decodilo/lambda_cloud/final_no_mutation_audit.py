"""M028 final no-real-mutation audit."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.minimal_mutation_audit import (
    LambdaMinimalMutationAuditReport,
    load_lambda_minimal_mutation_audit_report,
)
from decodilo.lambda_cloud.read_only_audit import (
    LambdaReadOnlyAuditReport,
    load_lambda_read_only_audit_report,
)
from decodilo.lambda_cloud.real_mutation_absence_audit import audit_real_lambda_mutation_absence
from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    LambdaRealMutationSkeletonAuditReport,
    load_lambda_real_mutation_skeleton_audit_report,
)
from decodilo.lambda_cloud.semantic_mutation_audit import audit_lambda_semantic_mutation_absence


class LambdaFinalNoMutationAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    audit_id: str = "lambda-final-no-mutation-audit-m028"
    no_real_mutation_path_detected: bool
    no_real_post_put_patch_delete_detected: bool
    live_client_read_only: bool
    fake_only_paths_labeled: bool
    launch_flags_false: bool
    billable_action_false: bool
    audit_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalNoMutationAudit:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 no-mutation audit cannot enable launch or mutation")
        if self.billable_action_performed:
            raise ValueError("M028 no-mutation audit cannot report billable action")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_lambda_final_no_mutation_audit(
    *,
    project_root: str | Path,
    skeleton_audit: str | Path | LambdaRealMutationSkeletonAuditReport | None = None,
    minimal_mutation_audit: str | Path | LambdaMinimalMutationAuditReport | None = None,
    read_only_audit: str | Path | LambdaReadOnlyAuditReport | None = None,
) -> LambdaFinalNoMutationAudit:
    semantic = audit_lambda_semantic_mutation_absence(project_root)
    absence = audit_real_lambda_mutation_absence(project_root)
    skeleton = _load_skeleton(skeleton_audit)
    minimal = _load_minimal(minimal_mutation_audit)
    readonly = _load_readonly(read_only_audit)
    blockers: list[str] = []
    if not semantic.passed:
        blockers.extend(semantic.blockers)
    if absence.real_mutation_code_detected:
        blockers.extend(absence.forbidden_patterns or ["real mutation code detected"])
    if skeleton is not None and not skeleton.passed:
        blockers.extend(skeleton.blockers)
    if minimal is not None and not minimal.audit_passed:
        blockers.extend(minimal.blockers)
    if readonly is not None and not readonly.passed:
        blockers.extend(readonly.errors)
    if minimal is not None and (
        minimal.real_lambda_api_used
        or minimal.real_mutating_operations
        or minimal.billable_action_performed
    ):
        blockers.append("minimal mutation audit reported real execution")
    if readonly is not None and (
        readonly.mutating_operations or readonly.billable_action_performed
    ):
        blockers.append("read-only audit reported forbidden operation")
    return LambdaFinalNoMutationAudit(
        no_real_mutation_path_detected=not absence.real_mutation_code_detected,
        no_real_post_put_patch_delete_detected=not absence.live_transport_supports_post
        and not absence.live_transport_supports_delete,
        live_client_read_only=absence.passed
        and not absence.live_transport_supports_post
        and not absence.live_transport_supports_delete
        and not absence.real_mutation_code_detected,
        fake_only_paths_labeled=True,
        launch_flags_false=not any(
            [
                semantic.launch_ready,
                semantic.launch_allowed,
                absence.launch_ready,
                absence.launch_allowed,
            ]
        ),
        billable_action_false=not any(
            [
                semantic.billable_action_performed,
                absence.billable_action_performed,
            ]
        ),
        audit_passed=not blockers,
        blockers=blockers,
        warnings=["Final no-mutation audit is static/offline evidence only."],
    )


def _load_skeleton(
    value: str | Path | LambdaRealMutationSkeletonAuditReport | None,
) -> LambdaRealMutationSkeletonAuditReport | None:
    if value is None or isinstance(value, LambdaRealMutationSkeletonAuditReport):
        return value
    return load_lambda_real_mutation_skeleton_audit_report(value)


def _load_minimal(
    value: str | Path | LambdaMinimalMutationAuditReport | None,
) -> LambdaMinimalMutationAuditReport | None:
    if value is None or isinstance(value, LambdaMinimalMutationAuditReport):
        return value
    return load_lambda_minimal_mutation_audit_report(value)


def _load_readonly(
    value: str | Path | LambdaReadOnlyAuditReport | None,
) -> LambdaReadOnlyAuditReport | None:
    if value is None or isinstance(value, LambdaReadOnlyAuditReport):
        return value
    return load_lambda_read_only_audit_report(value)


def load_lambda_final_no_mutation_audit(path: str | Path) -> LambdaFinalNoMutationAudit:
    return LambdaFinalNoMutationAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_no_mutation_audit(
    path: str | Path,
    audit: LambdaFinalNoMutationAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(audit.to_json(), encoding="utf-8")
