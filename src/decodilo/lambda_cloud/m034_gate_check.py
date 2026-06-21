"""M034 hard gate for third-attempt launch controls.

The gate is review/execution-preflight only. It does not send Lambda requests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_policy import m029_endpoint_for_operation
from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    LambdaEndpointSpecOperatorConfirmationReport,
    load_lambda_endpoint_spec_operator_confirmation,
)
from decodilo.lambda_cloud.launch_timeout_policy import (
    LambdaLaunchTimeoutPolicy,
    load_lambda_launch_timeout_policy,
)
from decodilo.lambda_cloud.m028_report import LambdaM028Report, load_lambda_m028_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.m033_report import LambdaM033Report, load_lambda_m033_report
from decodilo.lambda_cloud.response_capture_settings_lock import (
    LambdaResponseCaptureSettingsLock,
    load_lambda_response_capture_settings_lock,
)
from decodilo.lambda_cloud.third_attempt_authorization import (
    LambdaThirdAttemptAuthorization,
    load_lambda_third_attempt_authorization,
)
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    LambdaThirdAttemptCorrelationPlan,
    load_lambda_third_attempt_correlation_plan,
)
from decodilo.lambda_cloud.third_attempt_go_no_go import (
    LambdaThirdAttemptGoNoGoRecord,
    load_lambda_third_attempt_go_no_go,
)
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    LambdaThirdAttemptReconciliationPlan,
    load_lambda_third_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.third_attempt_risk_review import (
    LambdaThirdAttemptRiskReview,
    load_lambda_third_attempt_risk_review,
)


class LambdaM034GateCheckReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_id: str = "lambda-m034-third-attempt-gate-check"
    gate_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    effective_launch_timeout_seconds: float | None = None
    effective_terminate_timeout_seconds: float | None = None
    effective_read_only_verification_timeout_seconds: float | None = None
    response_capture_active: bool = False
    status_before_parse: bool = False
    body_sample_enabled: bool = False
    no_auto_launch_retry: bool = True
    endpoint_confirmation_status: str | None = None
    correlation_plan_status: str | None = None
    reconciliation_plan_status: str | None = None
    m034_authorization_status: str | None = None
    third_go_no_go_status: str | None = None
    m033_report_passed: bool = False
    endpoint_confirmation_hash: str | None = None
    response_capture_lock_hash: str | None = None
    timeout_policy_hash: str | None = None
    risk_review_hash: str | None = None
    correlation_plan_hash: str | None = None
    launch_idempotency_key_hash: str | None = None
    reconciliation_plan_hash: str | None = None
    m034_authorization_hash: str | None = None
    third_go_no_go_hash: str | None = None
    m033_report_hash: str | None = None
    planned_shape: str | None = None
    planned_region: str | None = None
    candidate_confidence: str | None = None
    terminate_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034GateCheckReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M034 gate check cannot enable launch or mutation")
        if self.gate_passed and self.blockers:
            raise ValueError("M034 gate check cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m034_gate_check(
    *,
    m028_report: LambdaM028Report,
    m029_authorization: LambdaM029AuthorizationPackage,
    endpoint_confirmation: LambdaEndpointSpecOperatorConfirmationReport,
    response_capture_lock: LambdaResponseCaptureSettingsLock,
    timeout_policy: LambdaLaunchTimeoutPolicy,
    risk_review: LambdaThirdAttemptRiskReview,
    correlation_plan: LambdaThirdAttemptCorrelationPlan,
    reconciliation_plan: LambdaThirdAttemptReconciliationPlan,
    m034_authorization: LambdaThirdAttemptAuthorization,
    third_go_no_go: LambdaThirdAttemptGoNoGoRecord,
    m033_report: LambdaM033Report,
    artifact_hashes: dict[str, str] | None = None,
) -> LambdaM034GateCheckReport:
    artifact_hashes = artifact_hashes or {}
    blockers: list[str] = []
    warnings: list[str] = [
        "M034 gate check is non-mutating and does not authorize launch by itself"
    ]
    launch_auth = m029_authorization.launch_authorization

    if not m028_report.report_passed:
        blockers.append("m028_report_failed")
    if (
        m028_report.decision_record.status
        != "authorized_for_m029_one_instance_launch_attempt"
    ):
        blockers.append("m028_decision_not_authorized_for_m029_attempt")
    if not m029_authorization.package_passed:
        blockers.append("m029_authorization_package_failed")
    if not launch_auth.launch_authorized_for_next_milestone:
        blockers.append("m029_launch_not_authorized_for_next_milestone")
    if launch_auth.launch_authorized_now:
        blockers.append("m029_authorization_attempted_launch_now")
    if launch_auth.max_instances != 1:
        blockers.append("max_instances_not_one")
    if launch_auth.max_runtime_minutes > 30:
        blockers.append("max_runtime_exceeds_30_minutes")
    if launch_auth.max_budget > 50:
        blockers.append("max_budget_exceeds_50")

    _check_endpoint_confirmation(endpoint_confirmation, blockers)
    _check_response_capture_lock(response_capture_lock, blockers, warnings)
    _check_timeout_policy(timeout_policy, blockers)
    _check_risk_review(risk_review, blockers)
    _check_correlation_plan(
        correlation_plan,
        response_capture_lock,
        timeout_policy,
        launch_auth,
        blockers,
    )
    _check_reconciliation_plan(reconciliation_plan, blockers)
    _check_authorization_and_go_no_go(
        m034_authorization,
        third_go_no_go,
        m033_report,
        blockers,
    )

    status = endpoint_confirmation.confirmation.confirmation_status
    return LambdaM034GateCheckReport(
        gate_passed=not blockers,
        blockers=blockers,
        warnings=warnings,
        effective_launch_timeout_seconds=timeout_policy.launch_request_timeout_seconds,
        effective_terminate_timeout_seconds=timeout_policy.terminate_request_timeout_seconds,
        effective_read_only_verification_timeout_seconds=(
            timeout_policy.read_only_verification_timeout_seconds
        ),
        response_capture_active=response_capture_lock.lock_passed,
        status_before_parse=response_capture_lock.capture_http_status_before_parse,
        body_sample_enabled=response_capture_lock.body_sample_enabled,
        no_auto_launch_retry=timeout_policy.no_auto_launch_retry
        and correlation_plan.no_automatic_retry,
        endpoint_confirmation_status=status,
        correlation_plan_status="passed" if correlation_plan.plan_passed else "failed",
        reconciliation_plan_status="passed" if reconciliation_plan.plan_passed else "failed",
        m034_authorization_status=m034_authorization.status,
        third_go_no_go_status=third_go_no_go.status,
        m033_report_passed=m033_report.report_passed,
        endpoint_confirmation_hash=artifact_hashes.get("endpoint_confirmation"),
        response_capture_lock_hash=response_capture_lock.lock_hash,
        timeout_policy_hash=artifact_hashes.get("timeout_policy"),
        risk_review_hash=artifact_hashes.get("risk_review"),
        correlation_plan_hash=artifact_hashes.get("correlation_plan"),
        launch_idempotency_key_hash=_hash_text(correlation_plan.idempotency_key),
        reconciliation_plan_hash=artifact_hashes.get("reconciliation_plan"),
        m034_authorization_hash=artifact_hashes.get("m034_authorization"),
        third_go_no_go_hash=artifact_hashes.get("third_go_no_go"),
        m033_report_hash=artifact_hashes.get("m033_report"),
        planned_shape=correlation_plan.planned_shape,
        planned_region=correlation_plan.planned_region,
        candidate_confidence=reconciliation_plan.candidate_confidence,
        terminate_allowed=reconciliation_plan.terminate_allowed_for_candidate,
    )


def build_lambda_m034_gate_check_from_paths(
    *,
    m028_report: str | Path,
    m029_authorization: str | Path,
    endpoint_confirmation: str | Path,
    response_capture_lock: str | Path,
    timeout_policy: str | Path,
    risk_review: str | Path,
    correlation_plan: str | Path,
    reconciliation_plan: str | Path,
    m034_authorization: str | Path,
    third_go_no_go: str | Path,
    m033_report: str | Path,
) -> LambdaM034GateCheckReport:
    paths = {
        "m028_report": Path(m028_report),
        "m029_authorization": Path(m029_authorization),
        "endpoint_confirmation": Path(endpoint_confirmation),
        "response_capture_lock": Path(response_capture_lock),
        "timeout_policy": Path(timeout_policy),
        "risk_review": Path(risk_review),
        "correlation_plan": Path(correlation_plan),
        "reconciliation_plan": Path(reconciliation_plan),
        "m034_authorization": Path(m034_authorization),
        "third_go_no_go": Path(third_go_no_go),
        "m033_report": Path(m033_report),
    }
    return build_lambda_m034_gate_check(
        m028_report=load_lambda_m028_report(paths["m028_report"]),
        m029_authorization=load_lambda_m029_authorization_package(
            paths["m029_authorization"]
        ),
        endpoint_confirmation=load_lambda_endpoint_spec_operator_confirmation(
            paths["endpoint_confirmation"]
        ),
        response_capture_lock=load_lambda_response_capture_settings_lock(
            paths["response_capture_lock"]
        ),
        timeout_policy=load_lambda_launch_timeout_policy(paths["timeout_policy"]),
        risk_review=load_lambda_third_attempt_risk_review(paths["risk_review"]),
        correlation_plan=load_lambda_third_attempt_correlation_plan(
            paths["correlation_plan"]
        ),
        reconciliation_plan=load_lambda_third_attempt_reconciliation_plan(
            paths["reconciliation_plan"]
        ),
        m034_authorization=load_lambda_third_attempt_authorization(
            paths["m034_authorization"]
        ),
        third_go_no_go=load_lambda_third_attempt_go_no_go(paths["third_go_no_go"]),
        m033_report=load_lambda_m033_report(paths["m033_report"]),
        artifact_hashes={name: _file_hash(path) for name, path in paths.items()},
    )


def load_lambda_m034_gate_check(path: str | Path) -> LambdaM034GateCheckReport:
    return LambdaM034GateCheckReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_gate_check(
    path: str | Path,
    report: LambdaM034GateCheckReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _check_endpoint_confirmation(
    report: LambdaEndpointSpecOperatorConfirmationReport,
    blockers: list[str],
) -> None:
    if not report.confirmation_passed:
        blockers.append("endpoint_confirmation_failed")
    if report.confirmation.confirmation_status not in {
        "confirmed_medium_confidence_accepted",
        "confirmed_high_confidence",
    }:
        blockers.append("endpoint_confirmation_not_accepted")
    launch_endpoint = m029_endpoint_for_operation("launch_one_instance")
    terminate_endpoint = m029_endpoint_for_operation("terminate_owned_instance")
    if report.confirmation.launch_method.upper() != launch_endpoint.method:
        blockers.append("launch_endpoint_method_mismatch")
    if _normalize_path(report.confirmation.launch_path_template) != launch_endpoint.path:
        blockers.append("launch_endpoint_path_mismatch")
    if report.confirmation.terminate_method.upper() != terminate_endpoint.method:
        blockers.append("terminate_endpoint_method_mismatch")
    if _normalize_path(report.confirmation.terminate_path_template) != terminate_endpoint.path:
        blockers.append("terminate_endpoint_path_mismatch")


def _check_response_capture_lock(
    lock: LambdaResponseCaptureSettingsLock,
    blockers: list[str],
    warnings: list[str],
) -> None:
    if not lock.lock_passed:
        blockers.append("response_capture_lock_failed")
        blockers.extend(lock.blockers)
    required = {
        "capture_http_status_before_parse": lock.capture_http_status_before_parse,
        "capture_redacted_headers": lock.capture_redacted_headers,
        "capture_content_type": lock.capture_content_type,
        "capture_body_size": lock.capture_body_size,
        "distinguish_timeout": lock.distinguish_timeout,
        "distinguish_malformed_json": lock.distinguish_malformed_json,
        "distinguish_non_json_body": lock.distinguish_non_json_body,
        "distinguish_empty_body": lock.distinguish_empty_body,
        "secret_redaction_enabled": lock.secret_redaction_enabled,
    }
    blockers.extend(name for name, value in required.items() if not value)
    if lock.body_sample_enabled:
        blockers.append("response_body_sample_enabled_without_m034_justification")
    else:
        warnings.append("response body samples remain disabled for M034")


def _check_timeout_policy(
    policy: LambdaLaunchTimeoutPolicy,
    blockers: list[str],
) -> None:
    if not policy.policy_passed:
        blockers.append("timeout_policy_failed")
        blockers.extend(policy.blockers)
    if policy.launch_request_timeout_seconds < 30.0:
        blockers.append("launch_timeout_below_m034_minimum")
    if policy.terminate_request_timeout_seconds <= 0:
        blockers.append("terminate_timeout_missing")
    if policy.read_only_verification_timeout_seconds <= 0:
        blockers.append("read_only_verification_timeout_missing")
    if not policy.no_auto_launch_retry:
        blockers.append("automatic_launch_retry_allowed")


def _check_risk_review(
    risk_review: LambdaThirdAttemptRiskReview,
    blockers: list[str],
) -> None:
    if not risk_review.third_attempt_risk_passed:
        blockers.append("third_attempt_risk_review_failed")


def _check_correlation_plan(
    plan: LambdaThirdAttemptCorrelationPlan,
    lock: LambdaResponseCaptureSettingsLock,
    policy: LambdaLaunchTimeoutPolicy,
    launch_auth: Any,
    blockers: list[str],
) -> None:
    if not plan.plan_passed:
        blockers.append("third_attempt_correlation_plan_failed")
        blockers.extend(plan.blockers)
    if plan.idempotency_key in plan.prior_idempotency_keys:
        blockers.append("third_attempt_correlation_key_reuses_prior_key")
    if not plan.no_automatic_retry:
        blockers.append("third_attempt_correlation_allows_retry")
    if not plan.pre_launch_discovery_ref:
        blockers.append("third_attempt_pre_launch_discovery_ref_missing")
    if not plan.request_hash:
        blockers.append("third_attempt_request_hash_missing")
    if plan.response_capture_settings_lock_hash != lock.lock_hash:
        blockers.append("third_attempt_response_capture_lock_hash_mismatch")
    if plan.timeout_policy_id != policy.policy_id:
        blockers.append("third_attempt_timeout_policy_mismatch")
    if plan.planned_shape != launch_auth.planned_instance_type:
        blockers.append("third_attempt_planned_shape_mismatch")
    if plan.planned_region != launch_auth.planned_region:
        blockers.append("third_attempt_planned_region_mismatch")
    if plan.planned_image != launch_auth.image_ref:
        blockers.append("third_attempt_planned_image_mismatch")


def _check_reconciliation_plan(
    plan: LambdaThirdAttemptReconciliationPlan,
    blockers: list[str],
) -> None:
    if not plan.plan_passed:
        blockers.append("third_attempt_reconciliation_plan_failed")
        blockers.extend(plan.blockers)
    required = {
        "verify_and_terminate_owned_id_from_response": (
            plan.verify_and_terminate_owned_id_from_response
        ),
        "read_only_reconciliation_after_response_loss": (
            plan.read_only_reconciliation_after_response_loss
        ),
        "medium_low_none_candidate_not_automatically_terminable": (
            plan.medium_low_none_candidate_not_automatically_terminable
        ),
        "final_read_only_termination_verification_required": (
            plan.final_read_only_termination_verification_required
        ),
        "final_ledger_reconciliation_required": plan.final_ledger_reconciliation_required,
    }
    blockers.extend(name for name, value in required.items() if not value)
    if plan.candidate_confidence in {"medium", "low", "none"} and (
        plan.terminate_allowed_for_candidate
    ):
        blockers.append("low_confidence_candidate_termination_allowed")


def _check_authorization_and_go_no_go(
    authorization: LambdaThirdAttemptAuthorization,
    go_no_go: LambdaThirdAttemptGoNoGoRecord,
    report: LambdaM033Report,
    blockers: list[str],
) -> None:
    if authorization.status != "authorized_for_future_m034_third_launch_attempt":
        blockers.append("m034_authorization_not_authorized_for_third_attempt")
    if go_no_go.status != "go_for_future_m034_third_launch_review":
        blockers.append("third_attempt_go_no_go_not_go_for_m034_review")
    if not report.report_passed:
        blockers.append("m033_report_failed")
    if report.launch_ready or report.launch_allowed:
        blockers.append("m033_report_attempted_to_enable_launch")


def _normalize_path(path: str) -> str:
    return "/" + path.strip().lstrip("/").rstrip("/")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
