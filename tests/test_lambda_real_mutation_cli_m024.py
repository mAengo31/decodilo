import json
import subprocess
import sys

from lambda_m024_helpers import write_m024_prepare_inputs


def test_m024_cli_skeleton_audit(tmp_path) -> None:
    out = tmp_path / "skeleton-audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "real-mutation",
            "skeleton-audit",
            "--project-root",
            ".",
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["passed"] is True


def test_m024_cli_prepare_and_disabled_launch(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)
    prepare = tmp_path / "prepare.json"
    disabled = tmp_path / "disabled.json"

    prepare_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "real-mutation",
            "prepare-launch",
            "--proposal",
            str(refs["operation"]),
            "--operation-spec",
            str(refs["operation"]),
            "--budget-lock",
            str(refs["budget"]),
            "--idempotency-plan",
            str(refs["idempotency"]),
            "--resource-scope",
            str(refs["scope"]),
            "--out",
            str(prepare),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    disabled_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "real-mutation",
            "disabled-launch-test",
            "--prepare-launch",
            str(prepare),
            "--out",
            str(disabled),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert prepare_run.returncode == 0, prepare_run.stderr
    assert disabled_run.returncode == 0, disabled_run.stderr
    payload = json.loads(disabled.read_text(encoding="utf-8"))
    assert payload["disabled_transport_report"]["blocked_before_request_construction"] is True
    assert payload["launch_allowed"] is False
