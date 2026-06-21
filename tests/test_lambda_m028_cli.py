import json
import subprocess
import sys

from lambda_m028_helpers import write_m028_core_artifacts


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_m028_cli_offline_review_flow(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)
    snapshot_out = tmp_path / "cli-state-snapshot.json"
    budget_out = tmp_path / "cli-budget-lock.json"
    resource_out = tmp_path / "cli-resource-lock.json"
    window_out = tmp_path / "cli-window-lock.json"
    teardown_out = tmp_path / "cli-teardown-plan.json"
    operator_out = tmp_path / "cli-operator.json"
    audit_out = tmp_path / "cli-no-mutation-audit.json"
    authorization_out = tmp_path / "cli-m029-authorization.json"
    decision_out = tmp_path / "cli-m028-decision.json"
    report_out = tmp_path / "cli-m028-report.json"

    snapshot = _run(
        "lambda",
        "m028",
        "state-snapshot",
        "--discovery-report",
        str(paths["valid_discovery"]),
        "--m020-report",
        str(paths["m020"]),
        "--out",
        str(snapshot_out),
    )
    budget = _run(
        "lambda",
        "m028",
        "budget-lock",
        "--m020-report",
        str(paths["m020"]),
        "--out",
        str(budget_out),
    )
    resource = _run(
        "lambda",
        "m028",
        "resource-lock",
        "--m020-report",
        str(paths["m020"]),
        "--out",
        str(resource_out),
    )
    window = _run(
        "lambda",
        "m028",
        "launch-window-lock",
        "--max-runtime-minutes",
        "30",
        "--out",
        str(window_out),
    )
    teardown = _run("lambda", "m028", "teardown-plan", "--out", str(teardown_out))
    operator = _run(
        "lambda",
        "m028",
        "operator-confirmation-template",
        "--acknowledge-all",
        "--out",
        str(operator_out),
    )
    audit = _run(
        "lambda",
        "m028",
        "final-no-mutation-audit",
        "--project-root",
        ".",
        "--out",
        str(audit_out),
    )
    authorization = _run(
        "lambda",
        "m028",
        "authorize-m029",
        "--state-snapshot",
        str(snapshot_out),
        "--budget-lock",
        str(budget_out),
        "--resource-lock",
        str(resource_out),
        "--launch-window-lock",
        str(window_out),
        "--teardown-plan",
        str(teardown_out),
        "--operator-confirmation",
        str(operator_out),
        "--no-mutation-audit",
        str(audit_out),
        "--out",
        str(authorization_out),
    )
    decision = _run(
        "lambda",
        "m028",
        "decision",
        "--m029-authorization",
        str(authorization_out),
        "--state-snapshot",
        str(snapshot_out),
        "--no-mutation-audit",
        str(audit_out),
        "--out",
        str(decision_out),
    )
    report = _run(
        "lambda",
        "m028",
        "report",
        "--decision",
        str(decision_out),
        "--m029-authorization",
        str(authorization_out),
        "--out",
        str(report_out),
    )

    assert snapshot["snapshot_passed"] is True
    assert budget["budget_lock_passed"] is True
    assert resource["resource_lock_passed"] is True
    assert window["launch_window_valid"] is True
    assert teardown["plan_passed"] is True
    assert operator["confirmation_complete_for_m029_authorization"] is True
    assert audit["audit_passed"] is True
    assert authorization["package_passed"] is True
    assert decision["status"] == "authorized_for_m029_one_instance_launch_attempt"
    assert report["report_passed"] is True
    assert report["launch_allowed"] is False
