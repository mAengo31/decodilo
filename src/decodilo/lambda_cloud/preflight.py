"""Lambda-specific offline preflight gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.credential_model import (
    LambdaCredentialPolicy,
    audit_lambda_credentials,
)
from decodilo.lambda_cloud.discovery import LambdaDiscoveryReport, load_lambda_discovery_report
from decodilo.lambda_cloud.evidence_freshness import (
    LambdaEvidenceFreshnessReport,
    load_lambda_evidence_freshness_report,
)
from decodilo.lambda_cloud.final_prelaunch_review import (
    LambdaFinalPrelaunchReviewReport,
    load_lambda_final_prelaunch_review,
)
from decodilo.lambda_cloud.first_launch_evidence_package import (
    LambdaFirstLaunchEvidencePackage,
    load_lambda_first_launch_evidence_package,
)
from decodilo.lambda_cloud.first_launch_safety_case import (
    LambdaFirstLaunchSafetyCase,
    load_lambda_first_launch_safety_case,
)
from decodilo.lambda_cloud.go_no_go_record import (
    LambdaGoNoGoRecord,
    load_lambda_go_no_go_record,
)
from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan, load_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.live_resource_ledger import (
    LambdaLiveResourceLedgerReport,
    load_lambda_live_ledger_report,
)
from decodilo.lambda_cloud.m020_report import (
    LambdaM020ReadinessReport,
    load_lambda_m020_report,
)
from decodilo.lambda_cloud.m027_authorization_record import (
    LambdaM027AuthorizationRecord,
    load_lambda_m027_authorization_record,
)
from decodilo.lambda_cloud.m028_report import LambdaM028Report, load_lambda_m028_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.m032_report import LambdaM032Report, load_lambda_m032_report
from decodilo.lambda_cloud.m033_report import LambdaM033Report, load_lambda_m033_report
from decodilo.lambda_cloud.m035_report import LambdaM035Report, load_lambda_m035_report
from decodilo.lambda_cloud.m036_report import LambdaM036Report, load_lambda_m036_report
from decodilo.lambda_cloud.m036r_report import LambdaM036RReport, load_lambda_m036r_report
from decodilo.lambda_cloud.m037_report import LambdaM037Report, load_lambda_m037_report
from decodilo.lambda_cloud.m037r_report import LambdaM037RReport, load_lambda_m037r_report
from decodilo.lambda_cloud.m038_report import LambdaM038Report, load_lambda_m038_report
from decodilo.lambda_cloud.m041_report import LambdaM041Report, load_lambda_m041_report
from decodilo.lambda_cloud.m043_report import LambdaM043Report, load_lambda_m043_report
from decodilo.lambda_cloud.m044_report import LambdaM044Report, load_lambda_m044_report
from decodilo.lambda_cloud.m045_report import LambdaM045Report, load_lambda_m045_report
from decodilo.lambda_cloud.m047_report import LambdaM047Report, load_lambda_m047_report
from decodilo.lambda_cloud.m050_report import LambdaM050Report, load_lambda_m050_report
from decodilo.lambda_cloud.m052_report import LambdaM052Report, load_lambda_m052_report
from decodilo.lambda_cloud.m053_report import LambdaM053Report, load_lambda_m053_report
from decodilo.lambda_cloud.m054a_report import LambdaM054AReport, load_lambda_m054a_report
from decodilo.lambda_cloud.minimal_mutation_audit import (
    LambdaMinimalMutationAuditReport,
    load_lambda_minimal_mutation_audit_report,
)
from decodilo.lambda_cloud.minimal_mutation_preflight import (
    LambdaMinimalMutationPreflightReport,
    load_lambda_minimal_mutation_preflight_report,
)
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard
from decodilo.lambda_cloud.read_only_audit import (
    LambdaReadOnlyAuditReport,
    load_lambda_read_only_audit_report,
)
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    LambdaRealLaunchBlockerMatrix,
    load_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.real_launch_decision_record import (
    LambdaRealLaunchDecisionRecord,
    load_lambda_real_launch_decision_record,
)
from decodilo.lambda_cloud.real_mutation_boundary_proposal import (
    LambdaRealMutationBoundaryProposal,
    load_lambda_real_mutation_boundary_proposal,
)
from decodilo.lambda_cloud.real_mutation_review_record import (
    LambdaRealMutationReviewRecord,
    load_lambda_real_mutation_review_record,
)
from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    LambdaRealMutationSkeletonAuditReport,
    load_lambda_real_mutation_skeleton_audit_report,
)
from decodilo.lambda_cloud.resource_ledger import (
    LambdaLedgerReconciliationReport,
    load_lambda_ledger_report,
)
from decodilo.lambda_cloud.resource_ownership_review import (
    LambdaResourceOwnershipReview,
    load_lambda_resource_ownership_review,
)
from decodilo.lambda_cloud.second_attempt_authorization import (
    LambdaSecondAttemptAuthorization,
    load_lambda_second_attempt_authorization,
)
from decodilo.lambda_cloud.second_attempt_go_no_go import (
    LambdaSecondAttemptGoNoGoRecord,
    load_lambda_second_attempt_go_no_go,
)
from decodilo.lambda_cloud.secret_handling_review import (
    LambdaSecretHandlingReview,
    load_lambda_secret_handling_review,
)
from decodilo.lambda_cloud.semantic_mutation_audit import (
    LambdaSemanticMutationAuditReport,
    load_lambda_semantic_mutation_audit_report,
)
from decodilo.lambda_cloud.spend_safety_review import (
    LambdaSpendSafetyReview,
    load_lambda_spend_safety_review,
)
from decodilo.lambda_cloud.teardown_plan import LambdaTeardownPlan, load_lambda_teardown_plan


class LambdaPreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    preflight_status: Literal[
        "passed_read_only",
        "passed_read_only_with_warnings",
        "failed",
    ] = "failed"
    launch_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    live_api_used: bool = False
    manual_review_required: bool = False
    mutation_guard: dict[str, Any]
    discovery_summary: dict[str, Any] | None = None
    credential_audit: dict[str, Any] | None = None
    ledger_summary: dict[str, Any] | None = None
    read_only_audit_summary: dict[str, Any] | None = None
    launch_plan_summary: dict[str, Any] | None = None
    teardown_plan_summary: dict[str, Any] | None = None
    m020_readiness_summary: dict[str, Any] | None = None
    m023_review_summary: dict[str, Any] | None = None
    real_mutation_skeleton_summary: dict[str, Any] | None = None
    m025_final_prelaunch_summary: dict[str, Any] | None = None
    m026_decision_summary: dict[str, Any] | None = None
    m027_minimal_mutation_summary: dict[str, Any] | None = None
    m028_final_authorization_summary: dict[str, Any] | None = None
    m029_run_summary: dict[str, Any] | None = None
    m030_second_attempt_summary: dict[str, Any] | None = None
    m032_response_loss_summary: dict[str, Any] | None = None
    m033_third_attempt_summary: dict[str, Any] | None = None
    m035_post_incident_summary: dict[str, Any] | None = None
    m036r_strand_compatibility_summary: dict[str, Any] | None = None
    m036_support_confirmation_summary: dict[str, Any] | None = None
    m037_support_response_summary: dict[str, Any] | None = None
    m037r_lower_cost_summary: dict[str, Any] | None = None
    m038_lower_cost_authorization_summary: dict[str, Any] | None = None
    m041_catalog_availability_summary: dict[str, Any] | None = None
    m043_capacity_followup_summary: dict[str, Any] | None = None
    m044_catalog_rotation_summary: dict[str, Any] | None = None
    m045_capacity_selected_summary: dict[str, Any] | None = None
    m047_lifecycle_smoke_closeout_summary: dict[str, Any] | None = None
    m050_remote_bootstrap_summary: dict[str, Any] | None = None
    m052_metadata_bootstrap_closeout_summary: dict[str, Any] | None = None
    m053_ssh_connectivity_planning_summary: dict[str, Any] | None = None
    m054a_ssh_connectivity_execution_summary: dict[str, Any] | None = None
    real_mutation_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_lambda_preflight(
    *,
    launch_plan: str | Path | LambdaLaunchPlan | None = None,
    teardown_plan: str | Path | LambdaTeardownPlan | None = None,
    ledger: str | Path | LambdaLedgerReconciliationReport | None = None,
    discovery_report: str | Path | LambdaDiscoveryReport | None = None,
    live_discovery_report: str | Path | LambdaLiveDiscoveryReport | None = None,
    read_only_audit: str | Path | LambdaReadOnlyAuditReport | None = None,
    live_ledger: str | Path | LambdaLiveResourceLedgerReport | None = None,
    credential_policy: LambdaCredentialPolicy | None = None,
    budget_manifest: str | Path | None = None,
    price_snapshot: str | Path | None = None,
    m020_report: str | Path | LambdaM020ReadinessReport | None = None,
    m023_proposal: str | Path | LambdaRealMutationBoundaryProposal | None = None,
    m023_safety_case: str | Path | LambdaFirstLaunchSafetyCase | None = None,
    m023_evidence_package: str | Path | LambdaFirstLaunchEvidencePackage | None = None,
    m023_review_record: str | Path | LambdaRealMutationReviewRecord | None = None,
    real_mutation_skeleton_audit: str
    | Path
    | LambdaRealMutationSkeletonAuditReport
    | None = None,
    m025_final_prelaunch_review: str | Path | LambdaFinalPrelaunchReviewReport | None = None,
    m025_go_no_go_record: str | Path | LambdaGoNoGoRecord | None = None,
    m025_semantic_mutation_audit: str | Path | LambdaSemanticMutationAuditReport | None = None,
    m025_spend_safety_review: str | Path | LambdaSpendSafetyReview | None = None,
    m025_secret_handling_review: str | Path | LambdaSecretHandlingReview | None = None,
    m025_resource_ownership_review: str
    | Path
    | LambdaResourceOwnershipReview
    | None = None,
    m026_decision_record: str | Path | LambdaRealLaunchDecisionRecord | None = None,
    m027_authorization_record: str | Path | LambdaM027AuthorizationRecord | None = None,
    m026_blocker_matrix: str | Path | LambdaRealLaunchBlockerMatrix | None = None,
    m026_evidence_freshness: str | Path | LambdaEvidenceFreshnessReport | None = None,
    m027_minimal_mutation_preflight: str
    | Path
    | LambdaMinimalMutationPreflightReport
    | None = None,
    m027_minimal_mutation_audit: str | Path | LambdaMinimalMutationAuditReport | None = None,
    m028_report: str | Path | LambdaM028Report | None = None,
    m029_authorization: str | Path | LambdaM029AuthorizationPackage | None = None,
    m029_report: str | Path | LambdaM029Report | None = None,
    m030_second_attempt_authorization: str
    | Path
    | LambdaSecondAttemptAuthorization
    | None = None,
    m030_second_attempt_go_no_go: str | Path | LambdaSecondAttemptGoNoGoRecord | None = None,
    m032_report: str | Path | LambdaM032Report | None = None,
    m033_report: str | Path | LambdaM033Report | None = None,
    m035_report: str | Path | LambdaM035Report | None = None,
    m036r_report: str | Path | LambdaM036RReport | None = None,
    m036_report: str | Path | LambdaM036Report | None = None,
    m037_report: str | Path | LambdaM037Report | None = None,
    m037r_report: str | Path | LambdaM037RReport | None = None,
    m038_report: str | Path | LambdaM038Report | None = None,
    m041_report: str | Path | LambdaM041Report | None = None,
    m043_report: str | Path | LambdaM043Report | None = None,
    m044_report: str | Path | LambdaM044Report | None = None,
    m045_report: str | Path | LambdaM045Report | None = None,
    m047_report: str | Path | LambdaM047Report | None = None,
    m050_report: str | Path | LambdaM050Report | None = None,
    m052_report: str | Path | LambdaM052Report | None = None,
    m053_report: str | Path | LambdaM053Report | None = None,
    m054a_report: str | Path | LambdaM054AReport | None = None,
) -> LambdaPreflightReport:
    warnings: list[str] = [
        "Lambda preflight is read-only/non-launching",
        "launch_ready=false and launch_allowed=false are enforced",
    ]
    errors: list[str] = []
    guard = LambdaMutationGuard()
    mutation_report = {
        "read_list_instances": guard.check("list_instances").model_dump(mode="json"),
        "launch_instance": guard.check("launch_instance").model_dump(mode="json"),
    }
    if mutation_report["launch_instance"]["allowed"]:
        errors.append("mutation guard unexpectedly allowed launch_instance")
    discovery = _load_discovery(discovery_report, warnings, errors)
    live_discovery = _load_live_discovery(live_discovery_report, warnings, errors)
    audit = _load_read_only_audit(read_only_audit, warnings, errors)
    plan = _load_launch_plan(launch_plan, warnings, errors)
    teardown = _load_teardown_plan(teardown_plan, warnings, errors)
    ledger_report = _load_ledger(ledger, warnings, errors, optional=live_ledger is not None)
    live_ledger_report = _load_live_ledger(live_ledger, warnings, errors)
    m020 = _load_m020_report(m020_report, warnings, errors)
    proposal = _load_m023_proposal(m023_proposal, warnings, errors)
    safety_case = _load_m023_safety_case(m023_safety_case, warnings, errors)
    evidence_package = _load_m023_evidence_package(m023_evidence_package, warnings, errors)
    review_record = _load_m023_review_record(m023_review_record, warnings, errors)
    skeleton_audit = _load_skeleton_audit(real_mutation_skeleton_audit, warnings, errors)
    m025_review = _load_m025_review(m025_final_prelaunch_review, warnings, errors)
    go_no_go = _load_go_no_go(m025_go_no_go_record, warnings, errors)
    semantic_audit = _load_semantic_audit(m025_semantic_mutation_audit, warnings, errors)
    spend_review = _load_spend_review(m025_spend_safety_review, warnings, errors)
    secret_review = _load_secret_review(m025_secret_handling_review, warnings, errors)
    ownership_review = _load_ownership_review(
        m025_resource_ownership_review,
        warnings,
        errors,
    )
    m026_decision = _load_m026_decision(m026_decision_record, warnings, errors)
    m027_auth = _load_m027_authorization(m027_authorization_record, warnings, errors)
    m026_matrix = _load_m026_matrix(m026_blocker_matrix, warnings, errors)
    m026_freshness = _load_m026_freshness(m026_evidence_freshness, warnings, errors)
    m027_minimal_preflight = _load_m027_minimal_preflight(
        m027_minimal_mutation_preflight,
        warnings,
        errors,
    )
    m027_minimal_audit = _load_m027_minimal_audit(
        m027_minimal_mutation_audit,
        warnings,
        errors,
    )
    m028 = _load_m028_report(m028_report, warnings, errors)
    m029 = _load_m029_authorization(m029_authorization, warnings, errors)
    m029_run = _load_m029_report(m029_report, warnings, errors)
    m030_authorization = _load_m030_second_attempt_authorization(
        m030_second_attempt_authorization,
        warnings,
        errors,
    )
    m030_go_no_go = _load_m030_second_attempt_go_no_go(
        m030_second_attempt_go_no_go,
        warnings,
        errors,
    )
    m032 = _load_m032_report(m032_report, warnings, errors)
    m033 = _load_m033_report(m033_report, warnings, errors)
    m035 = _load_m035_report(m035_report, warnings, errors)
    m036r = _load_m036r_report(m036r_report, warnings, errors)
    m036 = _load_m036_report(m036_report, warnings, errors)
    m037 = _load_m037_report(m037_report, warnings, errors)
    m037r = _load_m037r_report(m037r_report, warnings, errors)
    m038 = _load_m038_report(m038_report, warnings, errors)
    m041 = _load_m041_report(m041_report, warnings, errors)
    m043 = _load_m043_report(m043_report, warnings, errors)
    m044 = _load_m044_report(m044_report, warnings, errors)
    m045 = _load_m045_report(m045_report, warnings, errors)
    m047 = _load_m047_report(m047_report, warnings, errors)
    m050 = _load_m050_report(m050_report, warnings, errors)
    m052 = _load_m052_report(m052_report, warnings, errors)
    m053 = _load_m053_report(m053_report, warnings, errors)
    m054a = _load_m054a_report(m054a_report, warnings, errors)
    credential_audit = None
    if credential_policy is not None:
        try:
            credential_audit = audit_lambda_credentials(credential_policy)
            if not credential_audit.passed:
                errors.extend(credential_audit.errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Lambda credential policy invalid: {exc}")
    else:
        warnings.append("Lambda credential policy missing; only symbolic refs are allowed")
    if plan is not None:
        if plan.launch_enabled or plan.launch_allowed:
            errors.append(
                "Lambda launch plan must keep launch_enabled=false and launch_allowed=false"
            )
    if teardown is None:
        errors.append("missing Lambda teardown plan")
    elif teardown.teardown_enabled or teardown.live_resource_ids:
        errors.append("Lambda teardown plan must remain disabled and contain no live ids")
    if discovery is None and live_discovery is None:
        warnings.append("Lambda discovery report missing")
    elif discovery is not None and discovery.live_api_used:
        errors.append("M018 Lambda discovery must not use live API")
    if live_discovery is not None:
        if not live_discovery.read_only_mode:
            errors.append("Lambda live discovery must be read_only_mode=true")
        if not live_discovery.mutation_guard_enabled:
            errors.append("Lambda live discovery missing mutation guard")
        if not live_discovery.endpoint_policy_enabled:
            errors.append("Lambda live discovery missing endpoint policy")
        if not live_discovery.secret_redacted:
            errors.append("Lambda live discovery did not redact secrets")
        if live_discovery.billable_action_performed:
            errors.append("Lambda live discovery reported billable action")
        if any(result.mutation for result in live_discovery.endpoint_results):
            errors.append("Lambda live discovery reported mutating endpoint calibration")
        if not live_discovery.required_endpoint_success:
            errors.append("Lambda live discovery failed one or more required endpoints")
        if live_discovery.endpoint_count_failed_optional:
            warnings.append("Lambda live discovery had optional read-only endpoint failures")
        if live_discovery.endpoint_count_unsupported_optional:
            warnings.append("Lambda live discovery had unsupported optional endpoints")
    if audit is not None:
        if not audit.passed:
            errors.extend(f"Lambda read-only audit: {error}" for error in audit.errors)
        if audit.status == "passed_with_read_failures":
            warnings.append("Lambda read-only audit passed with read failures")
        if audit.billable_action_performed:
            errors.append("Lambda read-only audit reported billable action")
    elif live_discovery is not None:
        errors.append("Lambda live discovery requires read-only audit report")
    if live_ledger_report is not None:
        if not live_ledger_report.no_mutations_performed:
            errors.append("Lambda live ledger reported mutation")
        if live_ledger_report.billable_action_performed:
            errors.append("Lambda live ledger reported billable action")
        if live_ledger_report.manual_review_required:
            warnings.append("Lambda live ledger requires manual review for unmanaged resources")
    manual_review_required = bool(
        live_ledger_report is not None and live_ledger_report.manual_review_required
    )
    if budget_manifest is None:
        warnings.append("budget manifest missing for Lambda plan")
    if price_snapshot is None:
        warnings.append("price snapshot missing for Lambda plan")
    if m020 is None:
        warnings.append("M020 Lambda readiness report missing")
    else:
        if m020.billable_action_performed:
            errors.append("M020 readiness report recorded billable action")
        if m020.mutating_operations:
            errors.append("M020 readiness report recorded mutating operations")
        if m020.launch_allowed or m020.launch_ready:
            errors.append("M020 readiness report must keep launch flags false")
        if not m020.readiness_summary.future_fake_launch_lifecycle_candidate:
            warnings.append("M020 readiness is not a future fake launch lifecycle candidate")
    if proposal is None:
        warnings.append("M023 real mutation boundary proposal missing")
    else:
        if proposal.real_mutation_enabled or proposal.launch_ready or proposal.launch_allowed:
            errors.append("M023 proposal must keep real mutation and launch disabled")
    if safety_case is None:
        warnings.append("M023 first launch safety case missing")
    else:
        if (
            safety_case.real_mutation_enabled
            or safety_case.launch_ready
            or safety_case.launch_allowed
        ):
            errors.append("M023 safety case must keep real mutation and launch disabled")
        if not safety_case.safety_case_passed:
            warnings.append("M023 first launch safety case is not passed")
    if evidence_package is not None:
        if evidence_package.real_mutation_enabled or evidence_package.launch_ready:
            errors.append("M023 evidence package must not enable mutation or launch")
        if evidence_package.blockers:
            warnings.append("M023 evidence package has blockers")
    if review_record is not None:
        if review_record.real_mutation_enabled or review_record.launch_ready:
            errors.append("M023 review record must not enable mutation or launch")
        if review_record.status == "design_review_ready":
            warnings.append("design review ready only; real mutation remains disabled")
    if skeleton_audit is not None:
        if not skeleton_audit.passed:
            errors.append("M024 real mutation skeleton audit failed")
        if skeleton_audit.real_mutation_enabled or skeleton_audit.launch_allowed:
            errors.append("M024 skeleton audit must keep mutation and launch disabled")
        warnings.append("mutation skeleton present but disabled; no execution path available")
    if m025_review is not None:
        if m025_review.real_mutation_enabled or m025_review.launch_ready:
            errors.append("M025 final prelaunch review must not enable mutation or launch")
        if m025_review.blockers:
            warnings.append("M025 final prelaunch review has blockers")
    if go_no_go is not None:
        if go_no_go.real_mutation_enabled or go_no_go.launch_ready:
            errors.append("M025 go/no-go record must not enable mutation or launch")
        if go_no_go.status == "go_for_future_m026_real_launch_review":
            warnings.append(
                "future launch review candidate only; launch remains disabled in this build"
            )
    if semantic_audit is not None and not semantic_audit.passed:
        errors.append("M025 semantic mutation audit failed")
    if spend_review is not None and not spend_review.spend_safety_passed:
        warnings.append("M025 spend safety review has blockers")
    if secret_review is not None and not secret_review.secret_handling_passed:
        errors.append("M025 secret handling review failed")
    if ownership_review is not None and not ownership_review.resource_ownership_passed:
        warnings.append("M025 resource ownership review has blockers")
    if m026_decision is not None:
        if m026_decision.real_mutation_enabled or m026_decision.launch_ready:
            errors.append("M026 decision record must not enable mutation or launch")
        if m026_decision.status == "approve_m027_minimal_real_mutation_implementation":
            warnings.append("M027 implementation authorization only; launch remains disabled")
    if m027_auth is not None:
        if m027_auth.real_mutation_enabled or m027_auth.launch_ready:
            errors.append("M027 authorization record must not enable mutation or launch")
    if m026_matrix is not None and m026_matrix.real_launch_execution_blocked:
        warnings.append("M026 blocker matrix keeps real launch execution blocked")
    if m026_freshness is not None and not m026_freshness.freshness_passed:
        warnings.append("M026 evidence freshness requires more evidence")
    if m027_minimal_preflight is not None:
        if not m027_minimal_preflight.preflight_passed:
            errors.append("M027 minimal mutation fake-server preflight failed")
        if (
            m027_minimal_preflight.real_mutation_enabled
            or m027_minimal_preflight.launch_ready
            or m027_minimal_preflight.launch_allowed
            or m027_minimal_preflight.real_execution_allowed
        ):
            errors.append("M027 minimal mutation preflight must remain fake-server-only")
        warnings.append("M027 minimal mutation path is fake-server execution only")
    if m027_minimal_audit is not None:
        if not m027_minimal_audit.audit_passed:
            errors.append("M027 minimal mutation audit failed")
        if (
            m027_minimal_audit.real_lambda_api_used
            or m027_minimal_audit.real_mutating_operations
            or m027_minimal_audit.billable_action_performed
            or m027_minimal_audit.launch_ready
            or m027_minimal_audit.launch_allowed
        ):
            errors.append("M027 minimal mutation audit reported forbidden execution")
    if m028 is not None:
        if m028.real_mutation_enabled or m028.launch_ready or m028.launch_allowed:
            errors.append("M028 report must keep launch and mutation disabled")
        if m028.decision_record.status == "authorized_for_m029_one_instance_launch_attempt":
            warnings.append("M029 authorization only; M028 build remains non-launchable")
        if m028.blockers:
            warnings.append("M028 report has blockers")
    if m029 is not None:
        if m029.real_mutation_enabled or m029.launch_ready or m029.launch_allowed:
            errors.append("M029 authorization package must not enable launch in M028")
        if m029.launch_authorization.launch_authorized_now:
            errors.append("M029 authorization package must not authorize launch now")
        if m029.package_passed:
            warnings.append("M029 authorization only; M028 build remains non-launchable")
    if m029_run is not None:
        if m029_run.launch_ready or m029_run.launch_allowed:
            errors.append("M029 run report must keep launch flags false after completion")
        if m029_run.launch_request_sent and not m029_run.termination_verified:
            errors.append("M029 launch request was sent but termination was not verified")
        if m029_run.manual_review_required:
            warnings.append("M029 run report requires manual review")
    if m030_authorization is not None:
        if (
            m030_authorization.real_mutation_enabled
            or m030_authorization.launch_ready
            or m030_authorization.launch_allowed
        ):
            errors.append("M030 second-attempt authorization must not enable launch")
        if (
            m030_authorization.status
            == "authorized_for_future_m031_second_launch_attempt"
        ):
            warnings.append(
                "M031 second-attempt review authorization only; M030 remains non-launchable"
            )
    if m030_go_no_go is not None:
        if (
            m030_go_no_go.real_mutation_enabled
            or m030_go_no_go.launch_ready
            or m030_go_no_go.launch_allowed
        ):
            errors.append("M030 second-attempt go/no-go must not enable launch")
    if m032 is not None:
        if m032.launch_ready or m032.launch_allowed or m032.billable_action_performed:
            errors.append("M032 response-loss mitigation report must remain non-launchable")
        if m032.mitigation_accepted:
            warnings.append(
                "M032 response-loss mitigation accepted for future review only; "
                "launch remains disabled"
            )
        else:
            warnings.append("M032 response-loss mitigation has blockers")
    if m033 is not None:
        if (
            m033.launch_ready
            or m033.launch_allowed
            or m033.real_mutation_enabled
            or m033.billable_action_performed
        ):
            errors.append("M033 third-attempt report must remain non-launchable")
        if (
            m033.m034_authorization.status
            == "authorized_for_future_m034_third_launch_attempt"
        ):
            warnings.append(
                "M034 third-attempt review authorization only; M033 remains non-launchable"
            )
        if m033.blockers:
            warnings.append("M033 third-attempt review has blockers")
    if m035 is not None:
        if (
            m035.launch_ready
            or m035.launch_allowed
            or m035.real_mutation_enabled
            or m035.billable_action_performed
        ):
            errors.append("M035 post-incident strategy must remain non-launchable")
        warnings.append(
            "M035 post-incident strategy authorizes only a future milestone path"
        )
    if m036r is not None:
        if (
            m036r.launch_ready
            or m036r.launch_allowed
            or m036r.real_mutation_enabled
            or m036r.billable_action_performed
        ):
            errors.append("M036R Strand compatibility report must remain non-launchable")
        warnings.append(
            "M036R Strand compatibility is unofficial behavioral evidence only"
        )
    if m036 is not None:
        if (
            m036.launch_ready
            or m036.launch_allowed
            or m036.real_mutation_enabled
            or m036.billable_action_performed
        ):
            errors.append("M036 support confirmation report must remain non-launchable")
        warnings.append(
            "M036 support confirmation and shape reauthorization are future-review only"
        )
    if m037 is not None:
        if (
            m037.launch_ready
            or m037.launch_allowed
            or m037.real_mutation_enabled
            or m037.billable_action_performed
        ):
            errors.append("M037 support response report must remain non-launchable")
        warnings.append(
            "M037 support response validation is future-review only and cannot launch"
        )
    if m037r is not None:
        if (
            m037r.launch_ready
            or m037r.launch_allowed
            or m037r.real_mutation_enabled
            or m037r.billable_action_performed
        ):
            errors.append("M037R lower-cost Strand package must remain non-launchable")
        warnings.append(
            "M037R lower-cost Strand-compatible package is future-review only"
        )
    if m038 is not None:
        if (
            m038.launch_ready
            or m038.launch_allowed
            or m038.real_mutation_enabled
            or m038.billable_action_performed
        ):
            errors.append("M038 lower-cost M039 authorization must remain non-launchable")
        warnings.append("M038 lower-cost authorization is future-review only")
    if m041 is not None:
        if (
            m041.launch_ready
            or m041.launch_allowed
            or m041.real_mutation_enabled
            or m041.billable_action_performed
        ):
            errors.append(
                "M041 catalog availability decision must remain non-launchable"
            )
        warnings.append("M041 catalog availability decision is future-review only")
    if m043 is not None:
        if (
            m043.launch_ready
            or m043.launch_allowed
            or m043.real_mutation_enabled
            or m043.billable_action_performed
        ):
            errors.append("M043 capacity follow-up must remain non-launchable")
        warnings.append("M043 capacity follow-up is future-review only")
    if m044 is not None:
        if (
            m044.launch_ready
            or m044.launch_allowed
            or m044.real_mutation_enabled
            or m044.billable_action_performed
        ):
            errors.append("M044 catalog rotation decision must remain non-launchable")
        warnings.append("M044 catalog rotation decision is future-review only")
    if m045 is not None:
        if (
            m045.launch_ready
            or m045.launch_allowed
            or m045.real_mutation_enabled
            or m045.billable_action_performed
        ):
            errors.append("M045 capacity-selected decision must remain non-launchable")
        warnings.append("M045 capacity-selected decision is future-review only")
    if m047 is not None:
        if (
            m047.launch_ready
            or m047.launch_allowed
            or m047.real_mutation_enabled
            or m047.billable_action_performed
        ):
            errors.append("M047 lifecycle smoke closeout must remain non-launchable")
        warnings.append("M047 lifecycle smoke closeout records historical evidence only")
    if m050 is not None:
        if (
            m050.launch_ready
            or m050.launch_allowed
            or m050.real_mutation_enabled
            or m050.billable_action_performed
        ):
            errors.append("M050 remote bootstrap plan must remain non-launchable")
        warnings.append("M050 remote bootstrap authorization is future-review only")
    if m052 is not None:
        if (
            m052.launch_ready
            or m052.launch_allowed
            or m052.real_mutation_enabled
            or m052.billable_action_performed
        ):
            errors.append("M052 metadata bootstrap closeout must remain non-launchable")
        warnings.append("M052 metadata bootstrap closeout records historical evidence only")
    if m053 is not None:
        if (
            m053.launch_ready
            or m053.launch_allowed
            or m053.real_mutation_enabled
            or m053.billable_action_performed
        ):
            errors.append("M053 SSH connectivity planning must remain non-launchable")
        warnings.append("M053 SSH connectivity planning performs no SSH or launch")
    if m054a is not None:
        if (
            m054a.launch_ready
            or m054a.launch_allowed
            or m054a.real_mutation_enabled
            or m054a.billable_action_performed
        ):
            errors.append("M054A SSH connectivity execution package must remain non-launchable")
        warnings.append("M054A prepares SSH connectivity only; it performs no SSH or launch")
    status: Literal[
        "passed_read_only",
        "passed_read_only_with_warnings",
        "failed",
    ]
    if errors:
        status = "failed"
    elif warnings or manual_review_required:
        status = "passed_read_only_with_warnings"
    else:
        status = "passed_read_only"
    return LambdaPreflightReport(
        passed=not errors,
        preflight_status=status,
        manual_review_required=manual_review_required,
        live_api_used=bool(live_discovery is not None and live_discovery.live_api_used),
        mutation_guard=mutation_report,
        discovery_summary=_discovery_summary(discovery, live_discovery),
        credential_audit=None
        if credential_audit is None
        else credential_audit.model_dump(mode="json"),
        ledger_summary=_ledger_summary(ledger_report, live_ledger_report),
        read_only_audit_summary=None
        if audit is None
        else {
            "passed": audit.passed,
            "status": audit.status,
            "read_operations": audit.read_operations,
            "mutating_operations": audit.mutating_operations,
            "billable_action_performed": audit.billable_action_performed,
        },
        launch_plan_summary=None
        if plan is None
        else {
            "run_id": plan.run_id,
            "node_count": plan.node_count,
            "instance_type": plan.instance_type,
            "launch_enabled": plan.launch_enabled,
            "launch_allowed": plan.launch_allowed,
        },
        teardown_plan_summary=None
        if teardown is None
        else {
            "run_id": teardown.run_id,
            "teardown_enabled": teardown.teardown_enabled,
            "live_resource_ids": teardown.live_resource_ids,
        },
        m020_readiness_summary=None
        if m020 is None
        else {
            "m020_readiness_passed": m020.readiness_summary.m020_readiness_passed,
            "future_fake_launch_lifecycle_candidate": (
                m020.readiness_summary.future_fake_launch_lifecycle_candidate
            ),
            "future_real_launch_candidate": m020.readiness_summary.future_real_launch_candidate,
            "approval_passed": m020.approval_gate_report.approval_passed,
            "policy_passed": m020.first_launch_policy_report.policy_passed,
            "price_reconciliation_passed": (
                m020.price_reconciliation.price_reconciliation_passed
            ),
            "resource_reconciliation_passed": (
                m020.resource_reconciliation.resource_reconciliation_passed
            ),
            "blocker_count": len(m020.launch_blocker_report.blockers),
            "launch_ready": m020.launch_ready,
            "launch_allowed": m020.launch_allowed,
        },
        m023_review_summary=_m023_review_summary(
            proposal,
            safety_case,
            evidence_package,
            review_record,
        ),
        real_mutation_skeleton_summary=None
        if skeleton_audit is None
        else {
            "passed": skeleton_audit.passed,
            "real_mutation_code_detected": skeleton_audit.real_mutation_code_detected,
            "real_mutation_enabled": skeleton_audit.real_mutation_enabled,
            "launch_ready": skeleton_audit.launch_ready,
            "launch_allowed": skeleton_audit.launch_allowed,
            "message": "mutation skeleton present but disabled; no execution path available",
        },
        m025_final_prelaunch_summary=_m025_summary(
            m025_review,
            go_no_go,
            semantic_audit,
            spend_review,
            secret_review,
            ownership_review,
        ),
        m026_decision_summary=_m026_summary(
            m026_decision,
            m027_auth,
            m026_matrix,
            m026_freshness,
        ),
        m027_minimal_mutation_summary=_m027_minimal_summary(
            m027_minimal_preflight,
            m027_minimal_audit,
        ),
        m028_final_authorization_summary=_m028_summary(m028, m029),
        m029_run_summary=_m029_run_summary(m029_run),
        m030_second_attempt_summary=_m030_summary(m030_authorization, m030_go_no_go),
        m032_response_loss_summary=_m032_summary(m032),
        m033_third_attempt_summary=_m033_summary(m033),
        m035_post_incident_summary=_m035_summary(m035),
        m036r_strand_compatibility_summary=_m036r_summary(m036r),
        m036_support_confirmation_summary=_m036_summary(m036),
        m037_support_response_summary=_m037_summary(m037),
        m037r_lower_cost_summary=_m037r_summary(m037r),
        m038_lower_cost_authorization_summary=_m038_summary(m038),
        m041_catalog_availability_summary=_m041_summary(m041),
        m043_capacity_followup_summary=_m043_summary(m043),
        m044_catalog_rotation_summary=_m044_summary(m044),
        m045_capacity_selected_summary=_m045_summary(m045),
        m047_lifecycle_smoke_closeout_summary=_m047_summary(m047),
        m050_remote_bootstrap_summary=_m050_summary(m050),
        m052_metadata_bootstrap_closeout_summary=_m052_summary(m052),
        m053_ssh_connectivity_planning_summary=_m053_summary(m053),
        m054a_ssh_connectivity_execution_summary=_m054a_summary(m054a),
        warnings=warnings,
        errors=errors,
    )


def _discovery_summary(
    discovery: LambdaDiscoveryReport | None,
    live_discovery: LambdaLiveDiscoveryReport | None,
) -> dict[str, Any] | None:
    if live_discovery is not None:
        return {
            "regions": len(live_discovery.regions),
            "instance_types": len(live_discovery.instance_types),
            "running_instances": len(live_discovery.instances),
            "source": live_discovery.source,
            "live_api_used": live_discovery.live_api_used,
            "read_only_mode": live_discovery.read_only_mode,
            "endpoint_set": live_discovery.endpoint_set,
            "endpoint_count_attempted": live_discovery.endpoint_count_attempted,
            "endpoint_count_succeeded": live_discovery.endpoint_count_succeeded,
            "endpoint_count_failed": live_discovery.endpoint_count_failed,
            "endpoint_count_failed_required": live_discovery.endpoint_count_failed_required,
            "endpoint_count_failed_optional": live_discovery.endpoint_count_failed_optional,
            "endpoint_count_unsupported_optional": (
                live_discovery.endpoint_count_unsupported_optional
            ),
            "required_endpoint_success": live_discovery.required_endpoint_success,
            "optional_endpoint_warnings": live_discovery.optional_endpoint_warnings,
            "pagination_observed": live_discovery.pagination_observed,
            "redaction_mode": live_discovery.redaction_mode,
            "secret_source": live_discovery.secret_source,
            "secret_loaded": live_discovery.secret_loaded,
            "billable_action_performed": live_discovery.billable_action_performed,
        }
    if discovery is not None:
        return {
            "regions": len(discovery.regions),
            "instance_types": len(discovery.instance_types),
            "running_instances": len(discovery.running_instances),
            "source": discovery.source,
            "live_api_used": discovery.live_api_used,
        }
    return None


def _ledger_summary(
    ledger_report: LambdaLedgerReconciliationReport | None,
    live_ledger_report: LambdaLiveResourceLedgerReport | None,
) -> dict[str, Any] | None:
    if live_ledger_report is not None:
        return {
            "planned_count": live_ledger_report.planned_count,
            "discovered_count": live_ledger_report.discovered_count,
            "unmanaged_count": live_ledger_report.unmanaged_count,
            "orphan_candidates": live_ledger_report.unmanaged_instance_ids,
            "billable_state_count": live_ledger_report.billable_state_count,
            "manual_review_required": live_ledger_report.manual_review_required,
            "live_api_used": live_ledger_report.live_api_used,
            "no_mutations_performed": live_ledger_report.no_mutations_performed,
        }
    if ledger_report is not None:
        return {
            "planned_count": ledger_report.planned_count,
            "discovered_count": ledger_report.discovered_count,
            "unmanaged_count": ledger_report.unmanaged_count,
            "orphan_candidates": ledger_report.orphan_candidates,
        }
    return None


def _m023_review_summary(
    proposal: LambdaRealMutationBoundaryProposal | None,
    safety_case: LambdaFirstLaunchSafetyCase | None,
    evidence_package: LambdaFirstLaunchEvidencePackage | None,
    review_record: LambdaRealMutationReviewRecord | None,
) -> dict[str, Any] | None:
    if (
        proposal is None
        and safety_case is None
        and evidence_package is None
        and review_record is None
    ):
        return None
    return {
        "proposal_status": None if proposal is None else proposal.boundary_status,
        "safety_case_passed": None if safety_case is None else safety_case.safety_case_passed,
        "evidence_complete": None
        if evidence_package is None
        else evidence_package.evidence_complete,
        "review_status": None if review_record is None else review_record.status,
        "real_mutation_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "design review ready only; real mutation remains disabled",
    }


def _m025_summary(
    review: LambdaFinalPrelaunchReviewReport | None,
    go_no_go: LambdaGoNoGoRecord | None,
    semantic: LambdaSemanticMutationAuditReport | None,
    spend: LambdaSpendSafetyReview | None,
    secret: LambdaSecretHandlingReview | None,
    ownership: LambdaResourceOwnershipReview | None,
) -> dict[str, Any] | None:
    if all(item is None for item in [review, go_no_go, semantic, spend, secret, ownership]):
        return None
    return {
        "final_review_recommendation": None
        if review is None
        else review.go_no_go_recommendation,
        "go_no_go_status": None if go_no_go is None else go_no_go.status,
        "semantic_audit_passed": None if semantic is None else semantic.passed,
        "spend_safety_passed": None if spend is None else spend.spend_safety_passed,
        "secret_handling_passed": None if secret is None else secret.secret_handling_passed,
        "resource_ownership_passed": None
        if ownership is None
        else ownership.resource_ownership_passed,
        "real_mutation_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "future launch review candidate only; launch remains disabled in this build",
    }


def load_lambda_preflight_report(path: str | Path) -> LambdaPreflightReport:
    return LambdaPreflightReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_preflight_report(path: str | Path, report: LambdaPreflightReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _load_discovery(
    value: str | Path | LambdaDiscoveryReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaDiscoveryReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaDiscoveryReport):
        return value
    try:
        return load_lambda_discovery_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda discovery report unreadable: {exc}")
        warnings.append("Lambda discovery report could not be loaded")
        return None


def _load_live_discovery(
    value: str | Path | LambdaLiveDiscoveryReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaLiveDiscoveryReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaLiveDiscoveryReport):
        return value
    try:
        return load_lambda_live_discovery_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda live discovery report unreadable: {exc}")
        warnings.append("Lambda live discovery report could not be loaded")
        return None


def _load_read_only_audit(
    value: str | Path | LambdaReadOnlyAuditReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaReadOnlyAuditReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaReadOnlyAuditReport):
        return value
    try:
        return load_lambda_read_only_audit_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda read-only audit unreadable: {exc}")
        warnings.append("Lambda read-only audit could not be loaded")
        return None


def _load_launch_plan(
    value: str | Path | LambdaLaunchPlan | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaLaunchPlan | None:
    if value is None:
        warnings.append("Lambda launch plan missing")
        return None
    if isinstance(value, LambdaLaunchPlan):
        return value
    try:
        return load_lambda_launch_plan(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda launch plan unreadable: {exc}")
        return None


def _load_teardown_plan(
    value: str | Path | LambdaTeardownPlan | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaTeardownPlan | None:
    if value is None:
        warnings.append("Lambda teardown plan missing")
        return None
    if isinstance(value, LambdaTeardownPlan):
        return value
    try:
        return load_lambda_teardown_plan(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda teardown plan unreadable: {exc}")
        return None


def _load_ledger(
    value: str | Path | LambdaLedgerReconciliationReport | None,
    warnings: list[str],
    errors: list[str],
    *,
    optional: bool = False,
) -> LambdaLedgerReconciliationReport | None:
    if value is None:
        if not optional:
            warnings.append("Lambda resource ledger missing")
        return None
    if isinstance(value, LambdaLedgerReconciliationReport):
        return value
    try:
        return load_lambda_ledger_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda resource ledger unreadable: {exc}")
        return None


def _load_live_ledger(
    value: str | Path | LambdaLiveResourceLedgerReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaLiveResourceLedgerReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaLiveResourceLedgerReport):
        return value
    try:
        return load_lambda_live_ledger_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda live resource ledger unreadable: {exc}")
        warnings.append("Lambda live resource ledger could not be loaded")
        return None


def _load_m020_report(
    value: str | Path | LambdaM020ReadinessReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM020ReadinessReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaM020ReadinessReport):
        return value
    try:
        return load_lambda_m020_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M020 readiness report unreadable: {exc}")
        warnings.append("Lambda M020 readiness report could not be loaded")
        return None


def _load_m023_proposal(
    value: str | Path | LambdaRealMutationBoundaryProposal | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaRealMutationBoundaryProposal | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealMutationBoundaryProposal):
        return value
    try:
        return load_lambda_real_mutation_boundary_proposal(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M023 proposal unreadable: {exc}")
        warnings.append("Lambda M023 proposal could not be loaded")
        return None


def _load_m023_safety_case(
    value: str | Path | LambdaFirstLaunchSafetyCase | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaFirstLaunchSafetyCase | None:
    if value is None:
        return None
    if isinstance(value, LambdaFirstLaunchSafetyCase):
        return value
    try:
        return load_lambda_first_launch_safety_case(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M023 safety case unreadable: {exc}")
        warnings.append("Lambda M023 safety case could not be loaded")
        return None


def _load_m023_evidence_package(
    value: str | Path | LambdaFirstLaunchEvidencePackage | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaFirstLaunchEvidencePackage | None:
    if value is None:
        return None
    if isinstance(value, LambdaFirstLaunchEvidencePackage):
        return value
    try:
        return load_lambda_first_launch_evidence_package(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M023 evidence package unreadable: {exc}")
        warnings.append("Lambda M023 evidence package could not be loaded")
        return None


def _load_m023_review_record(
    value: str | Path | LambdaRealMutationReviewRecord | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaRealMutationReviewRecord | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealMutationReviewRecord):
        return value
    try:
        return load_lambda_real_mutation_review_record(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M023 review record unreadable: {exc}")
        warnings.append("Lambda M023 review record could not be loaded")
        return None


def _load_skeleton_audit(
    value: str | Path | LambdaRealMutationSkeletonAuditReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaRealMutationSkeletonAuditReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealMutationSkeletonAuditReport):
        return value
    try:
        return load_lambda_real_mutation_skeleton_audit_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M024 skeleton audit unreadable: {exc}")
        warnings.append("Lambda M024 skeleton audit could not be loaded")
        return None


def _load_m025_review(
    value: str | Path | LambdaFinalPrelaunchReviewReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaFinalPrelaunchReviewReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaFinalPrelaunchReviewReport):
        return value
    try:
        return load_lambda_final_prelaunch_review(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M025 final prelaunch review unreadable: {exc}")
        warnings.append("Lambda M025 final prelaunch review could not be loaded")
        return None


def _load_go_no_go(
    value: str | Path | LambdaGoNoGoRecord | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaGoNoGoRecord | None:
    if value is None:
        return None
    if isinstance(value, LambdaGoNoGoRecord):
        return value
    try:
        return load_lambda_go_no_go_record(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M025 go/no-go record unreadable: {exc}")
        warnings.append("Lambda M025 go/no-go record could not be loaded")
        return None


def _load_semantic_audit(
    value: str | Path | LambdaSemanticMutationAuditReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaSemanticMutationAuditReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaSemanticMutationAuditReport):
        return value
    try:
        return load_lambda_semantic_mutation_audit_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M025 semantic audit unreadable: {exc}")
        warnings.append("Lambda M025 semantic audit could not be loaded")
        return None


def _load_spend_review(
    value: str | Path | LambdaSpendSafetyReview | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaSpendSafetyReview | None:
    if value is None:
        return None
    if isinstance(value, LambdaSpendSafetyReview):
        return value
    try:
        return load_lambda_spend_safety_review(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M025 spend review unreadable: {exc}")
        warnings.append("Lambda M025 spend review could not be loaded")
        return None


def _load_secret_review(
    value: str | Path | LambdaSecretHandlingReview | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaSecretHandlingReview | None:
    if value is None:
        return None
    if isinstance(value, LambdaSecretHandlingReview):
        return value
    try:
        return load_lambda_secret_handling_review(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M025 secret review unreadable: {exc}")
        warnings.append("Lambda M025 secret review could not be loaded")
        return None


def _load_ownership_review(
    value: str | Path | LambdaResourceOwnershipReview | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaResourceOwnershipReview | None:
    if value is None:
        return None
    if isinstance(value, LambdaResourceOwnershipReview):
        return value
    try:
        return load_lambda_resource_ownership_review(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M025 ownership review unreadable: {exc}")
        warnings.append("Lambda M025 ownership review could not be loaded")
        return None


def _load_m026_decision(
    value: str | Path | LambdaRealLaunchDecisionRecord | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaRealLaunchDecisionRecord | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealLaunchDecisionRecord):
        return value
    try:
        return load_lambda_real_launch_decision_record(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M026 decision record unreadable: {exc}")
        warnings.append("Lambda M026 decision record could not be loaded")
        return None


def _load_m027_authorization(
    value: str | Path | LambdaM027AuthorizationRecord | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM027AuthorizationRecord | None:
    if value is None:
        return None
    if isinstance(value, LambdaM027AuthorizationRecord):
        return value
    try:
        return load_lambda_m027_authorization_record(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M027 authorization record unreadable: {exc}")
        warnings.append("Lambda M027 authorization record could not be loaded")
        return None


def _load_m026_matrix(
    value: str | Path | LambdaRealLaunchBlockerMatrix | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaRealLaunchBlockerMatrix | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealLaunchBlockerMatrix):
        return value
    try:
        return load_lambda_real_launch_blocker_matrix(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M026 blocker matrix unreadable: {exc}")
        warnings.append("Lambda M026 blocker matrix could not be loaded")
        return None


def _load_m026_freshness(
    value: str | Path | LambdaEvidenceFreshnessReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaEvidenceFreshnessReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaEvidenceFreshnessReport):
        return value
    try:
        return load_lambda_evidence_freshness_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M026 evidence freshness unreadable: {exc}")
        warnings.append("Lambda M026 evidence freshness could not be loaded")
        return None


def _load_m027_minimal_preflight(
    value: str | Path | LambdaMinimalMutationPreflightReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaMinimalMutationPreflightReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaMinimalMutationPreflightReport):
        return value
    try:
        return load_lambda_minimal_mutation_preflight_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M027 minimal mutation preflight unreadable: {exc}")
        warnings.append("Lambda M027 minimal mutation preflight could not be loaded")
        return None


def _load_m027_minimal_audit(
    value: str | Path | LambdaMinimalMutationAuditReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaMinimalMutationAuditReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaMinimalMutationAuditReport):
        return value
    try:
        return load_lambda_minimal_mutation_audit_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M027 minimal mutation audit unreadable: {exc}")
        warnings.append("Lambda M027 minimal mutation audit could not be loaded")
        return None


def _load_m028_report(
    value: str | Path | LambdaM028Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM028Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM028Report):
        return value
    try:
        return load_lambda_m028_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M028 report unreadable: {exc}")
        warnings.append("Lambda M028 report could not be loaded")
        return None


def _load_m029_authorization(
    value: str | Path | LambdaM029AuthorizationPackage | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM029AuthorizationPackage | None:
    if value is None:
        return None
    if isinstance(value, LambdaM029AuthorizationPackage):
        return value
    try:
        return load_lambda_m029_authorization_package(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M029 authorization package unreadable: {exc}")
        warnings.append("Lambda M029 authorization package could not be loaded")
        return None


def _load_m029_report(
    value: str | Path | LambdaM029Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM029Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM029Report):
        return value
    try:
        return load_lambda_m029_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M029 report unreadable: {exc}")
        warnings.append("Lambda M029 report could not be loaded")
        return None


def _load_m030_second_attempt_authorization(
    value: str | Path | LambdaSecondAttemptAuthorization | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaSecondAttemptAuthorization | None:
    if value is None:
        return None
    if isinstance(value, LambdaSecondAttemptAuthorization):
        return value
    try:
        return load_lambda_second_attempt_authorization(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M030 second-attempt authorization unreadable: {exc}")
        warnings.append("Lambda M030 second-attempt authorization could not be loaded")
        return None


def _load_m030_second_attempt_go_no_go(
    value: str | Path | LambdaSecondAttemptGoNoGoRecord | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaSecondAttemptGoNoGoRecord | None:
    if value is None:
        return None
    if isinstance(value, LambdaSecondAttemptGoNoGoRecord):
        return value
    try:
        return load_lambda_second_attempt_go_no_go(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M030 second-attempt go/no-go unreadable: {exc}")
        warnings.append("Lambda M030 second-attempt go/no-go could not be loaded")
        return None


def _load_m032_report(
    value: str | Path | LambdaM032Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM032Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM032Report):
        return value
    try:
        return load_lambda_m032_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M032 response-loss report unreadable: {exc}")
        warnings.append("Lambda M032 response-loss report could not be loaded")
        return None


def _load_m033_report(
    value: str | Path | LambdaM033Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM033Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM033Report):
        return value
    try:
        return load_lambda_m033_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M033 third-attempt report unreadable: {exc}")
        warnings.append("Lambda M033 third-attempt report could not be loaded")
        return None


def _load_m035_report(
    value: str | Path | LambdaM035Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM035Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM035Report):
        return value
    try:
        return load_lambda_m035_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M035 post-incident strategy report unreadable: {exc}")
        warnings.append("Lambda M035 post-incident strategy report could not be loaded")
        return None


def _load_m036_report(
    value: str | Path | LambdaM036Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM036Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM036Report):
        return value
    try:
        return load_lambda_m036_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M036 support confirmation report unreadable: {exc}")
        warnings.append("Lambda M036 support confirmation report could not be loaded")
        return None


def _load_m036r_report(
    value: str | Path | LambdaM036RReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM036RReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaM036RReport):
        return value
    try:
        return load_lambda_m036r_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M036R Strand compatibility report unreadable: {exc}")
        warnings.append("Lambda M036R Strand compatibility report could not be loaded")
        return None


def _load_m037_report(
    value: str | Path | LambdaM037Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM037Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM037Report):
        return value
    try:
        return load_lambda_m037_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M037 support response report unreadable: {exc}")
        warnings.append("Lambda M037 support response report could not be loaded")
        return None


def _load_m037r_report(
    value: str | Path | LambdaM037RReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM037RReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaM037RReport):
        return value
    try:
        return load_lambda_m037r_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M037R lower-cost report unreadable: {exc}")
        warnings.append("Lambda M037R lower-cost report could not be loaded")
        return None


def _load_m038_report(
    value: str | Path | LambdaM038Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM038Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM038Report):
        return value
    try:
        return load_lambda_m038_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M038 lower-cost authorization report unreadable: {exc}")
        warnings.append("Lambda M038 lower-cost authorization report could not be loaded")
        return None


def _load_m041_report(
    value: str | Path | LambdaM041Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM041Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM041Report):
        return value
    try:
        return load_lambda_m041_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M041 catalog availability report unreadable: {exc}")
        warnings.append("Lambda M041 catalog availability report could not be loaded")
        return None


def _load_m043_report(
    value: str | Path | LambdaM043Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM043Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM043Report):
        return value
    try:
        return load_lambda_m043_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M043 capacity follow-up report unreadable: {exc}")
        warnings.append("Lambda M043 capacity follow-up report could not be loaded")
        return None


def _load_m044_report(
    value: str | Path | LambdaM044Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM044Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM044Report):
        return value
    try:
        return load_lambda_m044_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M044 catalog rotation report unreadable: {exc}")
        warnings.append("Lambda M044 catalog rotation report could not be loaded")
        return None


def _load_m045_report(
    value: str | Path | LambdaM045Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM045Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM045Report):
        return value
    try:
        return load_lambda_m045_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M045 capacity-selected report unreadable: {exc}")
        warnings.append("Lambda M045 capacity-selected report could not be loaded")
        return None


def _load_m047_report(
    value: str | Path | LambdaM047Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM047Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM047Report):
        return value
    try:
        return load_lambda_m047_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M047 lifecycle smoke closeout report unreadable: {exc}")
        warnings.append("Lambda M047 lifecycle smoke closeout report could not be loaded")
        return None


def _load_m050_report(
    value: str | Path | LambdaM050Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM050Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM050Report):
        return value
    try:
        return load_lambda_m050_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M050 remote bootstrap report unreadable: {exc}")
        warnings.append("Lambda M050 remote bootstrap report could not be loaded")
        return None


def _load_m052_report(
    value: str | Path | LambdaM052Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM052Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM052Report):
        return value
    try:
        return load_lambda_m052_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M052 metadata bootstrap closeout report unreadable: {exc}")
        warnings.append("Lambda M052 metadata bootstrap closeout report could not be loaded")
        return None


def _load_m053_report(
    value: str | Path | LambdaM053Report | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM053Report | None:
    if value is None:
        return None
    if isinstance(value, LambdaM053Report):
        return value
    try:
        return load_lambda_m053_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M053 SSH connectivity planning report unreadable: {exc}")
        warnings.append("Lambda M053 SSH connectivity planning report could not be loaded")
        return None


def _load_m054a_report(
    value: str | Path | LambdaM054AReport | None,
    warnings: list[str],
    errors: list[str],
) -> LambdaM054AReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaM054AReport):
        return value
    try:
        return load_lambda_m054a_report(value)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Lambda M054A SSH connectivity execution report unreadable: {exc}")
        warnings.append("Lambda M054A SSH connectivity execution report could not be loaded")
        return None


def _m026_summary(
    decision: LambdaRealLaunchDecisionRecord | None,
    authorization: LambdaM027AuthorizationRecord | None,
    matrix: LambdaRealLaunchBlockerMatrix | None,
    freshness: LambdaEvidenceFreshnessReport | None,
) -> dict[str, Any] | None:
    if all(item is None for item in [decision, authorization, matrix, freshness]):
        return None
    return {
        "decision_status": None if decision is None else decision.status,
        "m027_authorization_status": None if authorization is None else authorization.status,
        "m027_authorization_blocked": None
        if matrix is None
        else matrix.m027_authorization_blocked,
        "real_launch_execution_blocked": None
        if matrix is None
        else matrix.real_launch_execution_blocked,
        "freshness_passed": None if freshness is None else freshness.freshness_passed,
        "real_mutation_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M027 implementation authorization only; launch remains disabled",
    }


def _m027_minimal_summary(
    preflight: LambdaMinimalMutationPreflightReport | None,
    audit: LambdaMinimalMutationAuditReport | None,
) -> dict[str, Any] | None:
    if preflight is None and audit is None:
        return None
    return {
        "preflight_passed": None if preflight is None else preflight.preflight_passed,
        "audit_passed": None if audit is None else audit.audit_passed,
        "fake_server_execution_only": True,
        "real_execution_allowed": False,
        "real_mutation_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M027 minimal mutation path is fake-server-only; real launch disabled",
    }


def _m028_summary(
    report: LambdaM028Report | None,
    authorization: LambdaM029AuthorizationPackage | None,
) -> dict[str, Any] | None:
    if report is None and authorization is None:
        return None
    return {
        "decision_status": None if report is None else report.decision_record.status,
        "m029_package_passed": None
        if authorization is None
        else authorization.package_passed,
        "authorized_for_next_milestone": None
        if authorization is None
        else authorization.launch_authorization.launch_authorized_for_next_milestone,
        "launch_authorized_now": None
        if authorization is None
        else authorization.launch_authorization.launch_authorized_now,
        "real_mutation_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M029 authorization only; M028 build remains non-launchable",
    }


def _m029_run_summary(report: LambdaM029Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "real_lambda_api_used": report.real_lambda_api_used,
        "launch_request_sent": report.launch_request_sent,
        "termination_request_sent": report.termination_request_sent,
        "termination_verified": report.termination_verified,
        "manual_review_required": report.manual_review_required,
        "mutating_operations": report.mutating_operations,
        "billable_action_performed": report.billable_action_performed,
        "estimated_spend": report.estimated_spend,
        "launch_ready": False,
        "launch_allowed": False,
    }


def _m030_summary(
    authorization: LambdaSecondAttemptAuthorization | None,
    go_no_go: LambdaSecondAttemptGoNoGoRecord | None,
) -> dict[str, Any] | None:
    if authorization is None and go_no_go is None:
        return None
    return {
        "authorization_status": None if authorization is None else authorization.status,
        "go_no_go_status": None if go_no_go is None else go_no_go.status,
        "real_mutation_enabled": False,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M031 second-attempt review authorization only; M030 remains non-launchable",
    }


def _m032_summary(report: LambdaM032Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "response_capture_implemented": report.response_capture_implemented,
        "diagnostics_implemented": report.diagnostics_implemented,
        "endpoint_spec_status": report.endpoint_spec_status,
        "regression_harness_passed": report.regression_harness_passed,
        "mitigation_accepted": report.mitigation_accepted,
        "future_launch_hold_released_for_review": (
            report.future_launch_hold_released_for_review
        ),
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M032 response-loss mitigation is future-review evidence only; launch remains disabled"
        ),
    }


def _m033_summary(report: LambdaM033Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "endpoint_confirmation_status": (
            report.endpoint_confirmation.confirmation.confirmation_status
        ),
        "response_capture_lock_passed": (
            report.response_capture_settings_lock.lock_passed
        ),
        "timeout_policy_passed": report.timeout_policy.policy_passed,
        "risk_review_passed": report.risk_review.third_attempt_risk_passed,
        "correlation_plan_passed": report.correlation_plan.plan_passed,
        "reconciliation_plan_passed": report.reconciliation_plan.plan_passed,
        "authorization_status": report.m034_authorization.status,
        "go_no_go_status": report.go_no_go.status,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M034 third-attempt review authorization only; M033 remains non-launchable"
        ),
    }


def _m035_summary(report: LambdaM035Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "attempts_represented": report.attempt_history.attempts_represented,
        "response_loss_count": report.attempt_history.response_loss_count,
        "endpoint_confidence_current": (
            report.endpoint_confidence_review.endpoint_confidence_current
        ),
        "shape_strategy": report.shape_strategy_review.recommended_shape_strategy,
        "recommended_option": report.option_matrix.recommended_option,
        "decision_status": report.decision_record.status,
        "report_passed": report.report_passed,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M035 post-incident strategy is future-milestone review only; launch remains disabled"
        ),
    }


def _m036_summary(report: LambdaM036Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "support_request_created": report.support_request.required_question_count > 0,
        "support_response_present": report.support_response is not None,
        "validation_passed": None
        if report.validation is None
        else report.validation.validation_passed,
        "endpoint_confidence": None
        if report.endpoint_confidence_upgrade is None
        else report.endpoint_confidence_upgrade.upgraded_confidence,
        "lower_cost_shape_status": report.lower_cost_shape_review.decision.status,
        "recommended_lower_cost_shape": None
        if report.lower_cost_shape_review.recommended_candidate is None
        else report.lower_cost_shape_review.recommended_candidate.shape,
        "strategy_decision": report.strategy_decision.status,
        "report_passed": report.report_passed,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M036 support confirmation and lower-cost shape review are future-only; "
            "launch remains disabled"
        ),
    }


def _m036r_summary(report: LambdaM036RReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "compatibility_status": report.compatibility_status,
        "gaps_found": report.gaps_found,
        "migration_required": report.migration_required,
        "future_launch_review_status": report.future_launch_review_status,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M036R Strand compatibility audit is unofficial behavioral evidence only; "
            "launch remains disabled"
        ),
    }


def _m037_summary(report: LambdaM037Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "decision_status": report.decision.status,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M037 support response decision is future-only; launch remains disabled"
        ),
    }


def _m037r_summary(report: LambdaM037RReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "lower_cost_shape": report.lower_cost_shape,
        "strand_payload_compatible": report.strand_payload_compatible,
        "future_launch_decision": report.future_launch_decision,
        "future_launch_review_authorized": report.future_launch_review_authorized,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M037R lower-cost Strand-compatible package is future-only; launch remains disabled"
        ),
    }


def _m038_summary(report: LambdaM038Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "authorization_status": report.authorization_status,
        "gate_passed": report.gate_passed,
        "command_preview_status": report.command_preview_status,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M038 lower-cost M039 authorization is future-only; launch remains disabled"
        ),
    }


def _m041_summary(report: LambdaM041Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "risk_acceptance_status": report.risk_acceptance_status,
        "operator_decision_status": report.operator_decision_status,
        "m042_authorization_status": report.m042_authorization_status,
        "gate_check_status": report.gate_check_status,
        "command_preview_status": report.command_preview_status,
        "wait_plan_status": report.wait_plan_status,
        "future_m042_candidate": report.future_m042_candidate,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": (
            "M041 catalog availability package is future-only; launch remains disabled"
        ),
    }


def _m043_summary(report: LambdaM043Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "decision_status": report.decision_status,
        "selected_shape": report.selected_shape,
        "selected_region": report.selected_region,
        "future_review_allowed": report.future_review_allowed,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M043 capacity follow-up is future-only; launch remains disabled",
    }


def _m044_summary(report: LambdaM044Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "risk_acceptance_status": report.risk_acceptance_status,
        "operator_decision_status": report.operator_decision_status,
        "authorization_status": report.authorization_status,
        "command_preview_status": report.command_preview_status,
        "decision_status": report.decision_status,
        "selected_candidate": report.selected_candidate,
        "future_review_allowed": report.future_review_allowed,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M044 catalog rotation is future-only; launch remains disabled",
    }


def _m045_summary(report: LambdaM045Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "operator_approval_status": report.operator_approval_status,
        "authorization_status": report.m046_authorization_status,
        "gate_check_status": report.gate_check_status,
        "command_preview_status": report.command_preview_status,
        "decision_status": report.decision_status,
        "selected_candidate": report.selected_candidate,
        "future_launch_candidate": report.future_launch_candidate,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M045 capacity-selected review is future-only; launch remains disabled",
    }


def _m047_summary(report: LambdaM047Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "success_record_status": report.success_record_status,
        "reconciliation_status": report.reconciliation_status,
        "evidence_package_status": report.evidence_package_status,
        "closeout_status": report.closeout_status,
        "live_parser_status": report.live_parser_status,
        "live_region_selection": report.live_region_selection,
        "alias_resolution_status": report.alias_resolution_status,
        "price_join_status": report.price_join_status,
        "selected_candidate": report.selected_candidate,
        "selected_region": report.selected_region,
        "report_passed": report.report_passed,
        "historical_billable_action_performed": (
            report.historical_billable_action_performed
        ),
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M047 is closeout-only; launch remains disabled",
    }


def _m050_summary(report: LambdaM050Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "selected_bootstrap_mode": report.selected_bootstrap_mode,
        "ssh_approval_status": report.ssh_approval_status,
        "command_allowlist_status": report.command_allowlist_status,
        "package_install_policy_status": report.package_install_policy_status,
        "no_training_policy_status": report.no_training_policy_status,
        "risk_review_passed": report.risk_review_passed,
        "m051_authorization_status": report.m051_authorization_status,
        "runbook_preview_status": report.runbook_preview_status,
        "future_m051_review_authorized": report.future_m051_review_authorized,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M050 is remote-bootstrap planning only; launch remains disabled",
    }


def _m052_summary(report: LambdaM052Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "success_record_status": report.success_record_status,
        "reconciliation_status": report.reconciliation_status,
        "closeout_status": report.closeout_status,
        "no_remote_execution_attestation_status": (
            report.no_remote_execution_attestation_status
        ),
        "lifecycle_comparison_status": report.lifecycle_comparison_status,
        "strategy_update_status": report.strategy_update_status,
        "m053_decision": report.m053_decision,
        "selected_candidate": report.selected_candidate,
        "selected_region": report.selected_region,
        "report_passed": report.report_passed,
        "historical_billable_action_performed": (
            report.historical_billable_action_performed
        ),
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M052 is closeout-only; launch and remote execution remain disabled",
    }


def _m053_summary(report: LambdaM053Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "scope_status": report.scope_status,
        "credential_policy_status": report.credential_policy_status,
        "client_policy_status": report.client_policy_status,
        "operator_approval_status": report.operator_approval_status,
        "remote_command_prohibition_status": report.remote_command_prohibition_status,
        "file_transfer_prohibition_status": report.file_transfer_prohibition_status,
        "port_forwarding_prohibition_status": report.port_forwarding_prohibition_status,
        "risk_review_status": report.risk_review_status,
        "m054_authorization_status": report.m054_authorization_status,
        "runbook_preview_status": report.runbook_preview_status,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M053 is SSH-connectivity planning only; SSH and launch remain disabled",
    }


def _m054a_summary(report: LambdaM054AReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "execution_plan_status": report.execution_plan_status,
        "static_validation_status": report.static_validation_status,
        "reviewer_bridge_status": report.reviewer_bridge_status,
        "no_exec_audit_status": report.no_exec_audit_status,
        "command_preview_status": report.command_preview_status,
        "future_m054b_cli_flags_accepted": report.future_m054b_cli_flags_accepted,
        "report_passed": report.report_passed,
        "blockers": report.blockers,
        "launch_ready": False,
        "launch_allowed": False,
        "message": "M054A prepares future SSH connectivity only; SSH and launch remain disabled",
    }
