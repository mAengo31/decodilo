import json
import subprocess
import sys

from lambda_m027_helpers import write_m027_core_artifacts


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_minimal_mutation_cli_fake_run_preflight_audit(tmp_path):
    paths = write_m027_core_artifacts(tmp_path)
    preflight_out = tmp_path / "minimal-preflight.json"
    run_out = tmp_path / "fake-run" / "report.json"
    audit_out = tmp_path / "minimal-audit.json"
    block_out = tmp_path / "blocked-real-url.json"

    preflight = _run(
        "lambda",
        "minimal-mutation",
        "preflight",
        "--m027-authorization",
        str(paths["authorization"]),
        "--operation-spec",
        str(paths["operation"]),
        "--budget-lock",
        str(paths["budget"]),
        "--idempotency-plan",
        str(paths["idempotency"]),
        "--resource-scope",
        str(paths["scope"]),
        "--out",
        str(preflight_out),
    )
    fake_run = _run(
        "lambda",
        "minimal-mutation",
        "fake-run",
        "--m027-authorization",
        str(paths["authorization"]),
        "--operation-spec",
        str(paths["operation"]),
        "--budget-lock",
        str(paths["budget"]),
        "--idempotency-plan",
        str(paths["idempotency"]),
        "--resource-scope",
        str(paths["scope"]),
        "--teardown-plan",
        str(paths["teardown"]),
        "--workdir",
        str(tmp_path / "fake-run"),
        "--out",
        str(run_out),
    )
    audit = _run(
        "lambda",
        "minimal-mutation",
        "audit",
        "--fake-run-report",
        str(run_out),
        "--out",
        str(audit_out),
    )
    blocked = _run(
        "lambda",
        "minimal-mutation",
        "blocked-real-url-test",
        "--out",
        str(block_out),
    )

    assert preflight["preflight_passed"] is True
    assert fake_run["fake_launch_executed"] is True
    assert fake_run["fake_terminate_executed"] is True
    assert audit["audit_passed"] is True
    assert blocked["blocked"] is True
    assert fake_run["launch_allowed"] is False
    assert audit["billable_action_performed"] is False
