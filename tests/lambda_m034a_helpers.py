from __future__ import annotations

from pathlib import Path

from lambda_m031d_helpers import closed_m031_closeout
from lambda_m033_helpers import (
    endpoint_confirmation,
    hold_release,
    mitigation_acceptance,
    risk_review,
)

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    write_lambda_endpoint_spec_operator_confirmation,
)
from decodilo.lambda_cloud.launch_timeout_policy import (
    build_lambda_launch_timeout_policy,
    write_lambda_launch_timeout_policy,
)
from decodilo.lambda_cloud.m033_report import build_lambda_m033_report, write_lambda_m033_report
from decodilo.lambda_cloud.response_capture_settings_lock import (
    build_lambda_response_capture_settings_lock,
    write_lambda_response_capture_settings_lock,
)
from decodilo.lambda_cloud.third_attempt_authorization import (
    build_lambda_third_attempt_authorization,
    write_lambda_third_attempt_authorization,
)
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    build_lambda_third_attempt_correlation_plan,
    write_lambda_third_attempt_correlation_plan,
)
from decodilo.lambda_cloud.third_attempt_go_no_go import (
    build_lambda_third_attempt_go_no_go,
    write_lambda_third_attempt_go_no_go,
)
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    build_lambda_third_attempt_reconciliation_plan,
    write_lambda_third_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.third_attempt_risk_review import (
    write_lambda_third_attempt_risk_review,
)


def write_m034a_artifacts(
    tmp_path: Path,
    *,
    m029_authorization,
    launch_timeout_seconds: float = 30.0,
    no_auto_launch_retry: bool = True,
    capture_http_status_before_parse: bool = True,
    body_sample_enabled: bool = False,
    endpoint_accept_medium: bool = True,
    endpoint_confidence: str = "medium",
    candidate_confidence: str = "none",
) -> dict[str, Path]:
    endpoint = endpoint_confirmation(
        accept_medium=endpoint_accept_medium,
        confidence=endpoint_confidence,
    )
    capture_lock = build_lambda_response_capture_settings_lock(
        capture_http_status_before_parse=capture_http_status_before_parse,
        body_sample_enabled=body_sample_enabled,
        max_body_sample_bytes=128 if body_sample_enabled else None,
    )
    timeout_policy = build_lambda_launch_timeout_policy(
        launch_request_timeout_seconds=launch_timeout_seconds,
        no_auto_launch_retry=no_auto_launch_retry,
    )
    risk = risk_review()
    correlation = build_lambda_third_attempt_correlation_plan(
        m029_authorization=m029_authorization,
        response_capture_lock=capture_lock,
        timeout_policy=timeout_policy,
    )
    reconciliation = build_lambda_third_attempt_reconciliation_plan(
        candidate_confidence=candidate_confidence
    )
    authorization = build_lambda_third_attempt_authorization(
        m031_closeout=closed_m031_closeout(),
        mitigation_acceptance=mitigation_acceptance(),
        hold_release=hold_release(),
        endpoint_confirmation=endpoint,
        response_capture_lock=capture_lock,
        timeout_policy=timeout_policy,
        risk_review=risk,
        correlation_plan=correlation,
        reconciliation_plan=reconciliation,
        fresh_readonly_discovery_present=True,
        budget_resource_checks_valid=True,
        renewed_operator_approval_present=True,
    )
    go_no_go = build_lambda_third_attempt_go_no_go(authorization)
    report = build_lambda_m033_report(
        endpoint_confirmation=endpoint,
        response_capture_settings_lock=capture_lock,
        timeout_policy=timeout_policy,
        risk_review=risk,
        correlation_plan=correlation,
        reconciliation_plan=reconciliation,
        m034_authorization=authorization,
        go_no_go=go_no_go,
    )

    paths = {
        "endpoint_confirmation": tmp_path / "endpoint-confirmation.json",
        "response_capture_lock": tmp_path / "response-capture-lock.json",
        "timeout_policy": tmp_path / "timeout-policy.json",
        "risk_review": tmp_path / "risk-review.json",
        "correlation_plan": tmp_path / "correlation-plan.json",
        "reconciliation_plan": tmp_path / "reconciliation-plan.json",
        "m034_authorization": tmp_path / "m034-authorization.json",
        "third_go_no_go": tmp_path / "third-go-no-go.json",
        "m033_report": tmp_path / "m033-report.json",
    }
    write_lambda_endpoint_spec_operator_confirmation(paths["endpoint_confirmation"], endpoint)
    write_lambda_response_capture_settings_lock(paths["response_capture_lock"], capture_lock)
    write_lambda_launch_timeout_policy(paths["timeout_policy"], timeout_policy)
    write_lambda_third_attempt_risk_review(paths["risk_review"], risk)
    write_lambda_third_attempt_correlation_plan(paths["correlation_plan"], correlation)
    write_lambda_third_attempt_reconciliation_plan(
        paths["reconciliation_plan"],
        reconciliation,
    )
    write_lambda_third_attempt_authorization(paths["m034_authorization"], authorization)
    write_lambda_third_attempt_go_no_go(paths["third_go_no_go"], go_no_go)
    write_lambda_m033_report(paths["m033_report"], report)
    return paths


def m034_cli_args(paths: dict[str, Path]) -> list[str]:
    return [
        "--endpoint-confirmation",
        str(paths["endpoint_confirmation"]),
        "--response-capture-lock",
        str(paths["response_capture_lock"]),
        "--timeout-policy",
        str(paths["timeout_policy"]),
        "--risk-review",
        str(paths["risk_review"]),
        "--correlation-plan",
        str(paths["correlation_plan"]),
        "--reconciliation-plan",
        str(paths["reconciliation_plan"]),
        "--m034-authorization",
        str(paths["m034_authorization"]),
        "--third-go-no-go",
        str(paths["third_go_no_go"]),
        "--m033-report",
        str(paths["m033_report"]),
    ]
