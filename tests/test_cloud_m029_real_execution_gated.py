import subprocess
import sys

from lambda_m029_helpers import m029_fixture
from lambda_m030_helpers import closed_m029_incident, prior_m029_report

from decodilo.lambda_cloud.m029_incident_report import write_lambda_m029_incident_report
from decodilo.lambda_cloud.m029_report import write_lambda_m029_report
from decodilo.lambda_cloud.response_loss_mitigation_review import (
    build_lambda_response_loss_mitigation_review,
    write_lambda_response_loss_mitigation_review,
)
from decodilo.lambda_cloud.second_attempt_authorization import (
    build_lambda_second_attempt_authorization,
    write_lambda_second_attempt_authorization,
)
from decodilo.lambda_cloud.second_attempt_correlation_plan import (
    build_lambda_second_attempt_correlation_plan,
    write_lambda_second_attempt_correlation_plan,
)
from decodilo.lambda_cloud.second_attempt_go_no_go import (
    build_lambda_second_attempt_go_no_go,
    write_lambda_second_attempt_go_no_go,
)
from decodilo.lambda_cloud.second_attempt_reconciliation_plan import (
    build_lambda_second_attempt_reconciliation_plan,
    write_lambda_second_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.second_attempt_risk_review import (
    build_lambda_second_attempt_risk_review,
    write_lambda_second_attempt_risk_report,
)


def test_m029_cli_fake_run_and_missing_confirmation_blocks(tmp_path):
    fx = m029_fixture(tmp_path)
    workdir = tmp_path / "run"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--m028-report",
        str(fx["m028_report"]),
        "--m029-authorization",
        str(fx["m029_authorization"]),
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        "I understand this may create a billable Lambda instance and must be terminated",
        "--confirm-terminate-required",
        "I understand this run must terminate the owned instance and verify termination",
    ]
    ok = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert '"termination_verified": true' in ok.stdout
    assert '"billable_action_performed": false' in ok.stdout

    blocked = subprocess.run(cmd[:-1] + ["wrong"], check=False, capture_output=True, text=True)
    assert blocked.returncode != 0
    assert "launch_request_sent" in blocked.stdout


def test_m029_cli_second_attempt_uses_m030_correlation_key(tmp_path):
    fx = m029_fixture(tmp_path)
    incident = closed_m029_incident()
    prior = prior_m029_report()
    risk = build_lambda_second_attempt_risk_review(incident)
    mitigation = build_lambda_response_loss_mitigation_review(
        incident=incident,
        prior_m029_report=prior,
    )
    correlation = build_lambda_second_attempt_correlation_plan(
        prior_m029_report=prior,
        m029_authorization=fx["authorization"],
    )
    reconciliation = build_lambda_second_attempt_reconciliation_plan()
    authorization = build_lambda_second_attempt_authorization(
        incident=incident,
        risk_review=risk,
        mitigation_review=mitigation,
        correlation_plan=correlation,
        reconciliation_plan=reconciliation,
    )
    go_no_go = build_lambda_second_attempt_go_no_go(authorization)
    incident_path = tmp_path / "incident.json"
    prior_path = tmp_path / "prior.json"
    risk_path = tmp_path / "risk.json"
    mitigation_path = tmp_path / "mitigation.json"
    correlation_path = tmp_path / "correlation.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    second_auth_path = tmp_path / "second-auth.json"
    go_path = tmp_path / "go.json"
    write_lambda_m029_incident_report(incident_path, incident)
    write_lambda_m029_report(prior_path, prior)
    write_lambda_second_attempt_risk_report(risk_path, risk)
    write_lambda_response_loss_mitigation_review(mitigation_path, mitigation)
    write_lambda_second_attempt_correlation_plan(correlation_path, correlation)
    write_lambda_second_attempt_reconciliation_plan(reconciliation_path, reconciliation)
    write_lambda_second_attempt_authorization(second_auth_path, authorization)
    write_lambda_second_attempt_go_no_go(go_path, go_no_go)
    workdir = tmp_path / "second-run"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--m028-report",
        str(fx["m028_report"]),
        "--m029-authorization",
        str(fx["m029_authorization"]),
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        "I understand this may create a billable Lambda instance and must be terminated",
        "--confirm-terminate-required",
        "I understand this run must terminate the owned instance and verify termination",
        "--previous-incident-report",
        str(incident_path),
        "--second-risk-review",
        str(risk_path),
        "--second-mitigation-review",
        str(mitigation_path),
        "--second-correlation-plan",
        str(correlation_path),
        "--second-reconciliation-plan",
        str(reconciliation_path),
        "--second-authorization",
        str(second_auth_path),
        "--second-go-no-go",
        str(go_path),
    ]

    ok = subprocess.run(cmd, check=False, capture_output=True, text=True)

    assert ok.returncode == 0, ok.stderr
    gate_summary = (workdir / "second-attempt-gates.json").read_text(encoding="utf-8")
    assert correlation.idempotency_key in gate_summary
    assert correlation.second_attempt_id in gate_summary
    assert correlation.idempotency_key != "m029-launch_one_instance-b82d91373c9b57a5effadf13"
