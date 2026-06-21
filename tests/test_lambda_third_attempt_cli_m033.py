import json
import subprocess
import sys

from lambda_m029d_helpers import ambiguous_m029_report
from lambda_m030_helpers import m029_authorization_package
from lambda_m031d_helpers import closed_m031_closeout, closed_m031_incident
from lambda_m033_helpers import mitigation_acceptance

from decodilo.lambda_cloud.future_launch_hold_release import (
    evaluate_lambda_future_launch_hold_release,
    write_lambda_future_launch_hold_release,
)
from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec
from decodilo.lambda_cloud.launch_endpoint_verification import (
    verify_lambda_endpoint_specs,
    write_lambda_endpoint_verification_report,
)
from decodilo.lambda_cloud.m029_launch_authorization import (
    write_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.m029_report import write_lambda_m029_report
from decodilo.lambda_cloud.m031_incident_closeout import write_lambda_m031_incident_closeout
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    write_lambda_response_loss_mitigation_acceptance,
)


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_third_attempt_cli_flow_is_review_only(tmp_path):
    endpoint_spec = tmp_path / "endpoint.json"
    mitigation = tmp_path / "mitigation.json"
    hold = tmp_path / "hold.json"
    m029c_report = tmp_path / "m029c.json"
    m031_report = tmp_path / "m031.json"
    m031_closeout = tmp_path / "m031-closeout.json"
    m029_auth = tmp_path / "m029-auth.json"
    endpoint_confirmation = tmp_path / "endpoint-confirmation.json"
    capture_lock = tmp_path / "capture-lock.json"
    timeout_policy = tmp_path / "timeout-policy.json"
    risk_review = tmp_path / "risk.json"
    correlation_plan = tmp_path / "correlation.json"
    reconciliation_plan = tmp_path / "reconciliation.json"
    authorization = tmp_path / "authorization.json"
    go_no_go = tmp_path / "go-no-go.json"
    report_path = tmp_path / "m033.json"

    endpoint = verify_lambda_endpoint_specs(
        [
            build_lambda_endpoint_spec(
                operation="launch_one_instance",
                method="POST",
                path_template="/instance-operations/launch",
                source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
                confidence="medium",
            ),
            build_lambda_endpoint_spec(
                operation="terminate_owned_instance",
                method="POST",
                path_template="/instance-operations/terminate",
                source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
                confidence="medium",
            ),
        ]
    )
    write_lambda_endpoint_verification_report(endpoint_spec, endpoint)
    accepted = mitigation_acceptance()
    write_lambda_response_loss_mitigation_acceptance(mitigation, accepted)
    write_lambda_future_launch_hold_release(
        hold,
        evaluate_lambda_future_launch_hold_release(
            m031_incident_report=closed_m031_incident(),
            mitigation_acceptance=accepted,
        ),
    )
    write_lambda_m029_report(m029c_report, ambiguous_m029_report())
    write_lambda_m029_report(m031_report, ambiguous_m029_report())
    write_lambda_m031_incident_closeout(m031_closeout, closed_m031_closeout())
    write_lambda_m029_authorization_package(m029_auth, m029_authorization_package())

    endpoint_out = _run(
        "lambda",
        "third-attempt",
        "endpoint-confirmation",
        "--endpoint-spec",
        str(endpoint_spec),
        "--accept-medium-confidence",
        "--out",
        str(endpoint_confirmation),
    )
    capture_out = _run(
        "lambda",
        "third-attempt",
        "response-capture-lock",
        "--out",
        str(capture_lock),
    )
    timeout_out = _run(
        "lambda",
        "third-attempt",
        "timeout-policy",
        "--launch-timeout-seconds",
        "30",
        "--terminate-timeout-seconds",
        "30",
        "--read-only-verification-timeout-seconds",
        "120",
        "--out",
        str(timeout_policy),
    )
    risk_out = _run(
        "lambda",
        "third-attempt",
        "risk-review",
        "--m029c-report",
        str(m029c_report),
        "--m031-report",
        str(m031_report),
        "--m031d-closeout",
        str(m031_closeout),
        "--mitigation-acceptance",
        str(mitigation),
        "--endpoint-confirmation",
        str(endpoint_confirmation),
        "--timeout-policy",
        str(timeout_policy),
        "--out",
        str(risk_review),
    )
    correlation_out = _run(
        "lambda",
        "third-attempt",
        "correlation-plan",
        "--m029-authorization",
        str(m029_auth),
        "--response-capture-lock",
        str(capture_lock),
        "--timeout-policy",
        str(timeout_policy),
        "--out",
        str(correlation_plan),
    )
    reconciliation_out = _run(
        "lambda",
        "third-attempt",
        "reconciliation-plan",
        "--out",
        str(reconciliation_plan),
    )
    authorization_out = _run(
        "lambda",
        "third-attempt",
        "authorize",
        "--m031d-closeout",
        str(m031_closeout),
        "--mitigation-acceptance",
        str(mitigation),
        "--hold-release",
        str(hold),
        "--endpoint-confirmation",
        str(endpoint_confirmation),
        "--response-capture-lock",
        str(capture_lock),
        "--timeout-policy",
        str(timeout_policy),
        "--risk-review",
        str(risk_review),
        "--correlation-plan",
        str(correlation_plan),
        "--reconciliation-plan",
        str(reconciliation_plan),
        "--renewed-operator-approval",
        "--out",
        str(authorization),
    )
    go_out = _run(
        "lambda",
        "third-attempt",
        "go-no-go",
        "--authorization",
        str(authorization),
        "--out",
        str(go_no_go),
    )
    report = _run(
        "lambda",
        "third-attempt",
        "report",
        "--endpoint-confirmation",
        str(endpoint_confirmation),
        "--response-capture-lock",
        str(capture_lock),
        "--timeout-policy",
        str(timeout_policy),
        "--risk-review",
        str(risk_review),
        "--correlation-plan",
        str(correlation_plan),
        "--reconciliation-plan",
        str(reconciliation_plan),
        "--authorization",
        str(authorization),
        "--go-no-go",
        str(go_no_go),
        "--out",
        str(report_path),
    )

    assert endpoint_out["confirmation_passed"] is True
    assert capture_out["lock_passed"] is True
    assert timeout_out["policy_passed"] is True
    assert risk_out["third_attempt_risk_passed"] is True
    assert correlation_out["plan_passed"] is True
    assert reconciliation_out["plan_passed"] is True
    assert authorization_out["status"] == "authorized_for_future_m034_third_launch_attempt"
    assert go_out["status"] == "go_for_future_m034_third_launch_review"
    assert report["report_passed"] is True
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
