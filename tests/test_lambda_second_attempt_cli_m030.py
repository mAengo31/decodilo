import json
import subprocess
import sys

from lambda_m030_helpers import (
    closed_m029_incident,
    m029_authorization_package,
    prior_m029_report,
)

from decodilo.lambda_cloud.m029_incident_report import write_lambda_m029_incident_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    write_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.m029_report import write_lambda_m029_report


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_second_attempt_cli_review_flow(tmp_path):
    incident_path = tmp_path / "incident.json"
    prior_path = tmp_path / "prior-m029.json"
    authorization_path = tmp_path / "m029-authorization.json"
    risk_out = tmp_path / "risk.json"
    mitigation_out = tmp_path / "mitigation.json"
    correlation_out = tmp_path / "correlation.json"
    reconciliation_out = tmp_path / "reconciliation.json"
    second_auth_out = tmp_path / "second-auth.json"
    go_out = tmp_path / "go.json"
    write_lambda_m029_incident_report(incident_path, closed_m029_incident())
    write_lambda_m029_report(prior_path, prior_m029_report())
    write_lambda_m029_authorization_package(
        authorization_path,
        m029_authorization_package(),
    )

    risk = _run(
        "lambda",
        "second-attempt",
        "risk-review",
        "--incident-report",
        str(incident_path),
        "--out",
        str(risk_out),
    )
    mitigation = _run(
        "lambda",
        "second-attempt",
        "mitigation-review",
        "--incident-report",
        str(incident_path),
        "--prior-m029-report",
        str(prior_path),
        "--out",
        str(mitigation_out),
    )
    correlation = _run(
        "lambda",
        "second-attempt",
        "correlation-plan",
        "--prior-m029-report",
        str(prior_path),
        "--m029-authorization",
        str(authorization_path),
        "--out",
        str(correlation_out),
    )
    reconciliation = _run(
        "lambda",
        "second-attempt",
        "reconciliation-plan",
        "--out",
        str(reconciliation_out),
    )
    second_auth = _run(
        "lambda",
        "second-attempt",
        "authorize",
        "--incident-report",
        str(incident_path),
        "--risk-review",
        str(risk_out),
        "--mitigation-review",
        str(mitigation_out),
        "--correlation-plan",
        str(correlation_out),
        "--reconciliation-plan",
        str(reconciliation_out),
        "--out",
        str(second_auth_out),
    )
    go = _run(
        "lambda",
        "second-attempt",
        "go-no-go",
        "--authorization",
        str(second_auth_out),
        "--out",
        str(go_out),
    )

    assert risk["risk_review_passed"] is True
    assert mitigation["mitigation_passed"] is True
    assert correlation["plan_passed"] is True
    assert reconciliation["plan_passed"] is True
    assert second_auth["status"] == "authorized_for_future_m031_second_launch_attempt"
    assert go["status"] == "go_for_future_m031_second_launch_review"
    assert go["launch_allowed"] is False
