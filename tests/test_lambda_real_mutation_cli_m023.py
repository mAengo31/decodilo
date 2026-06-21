import json
import subprocess
import sys

from lambda_m023_helpers import write_m023_core_artifacts


def test_real_mutation_operation_spec_cli(tmp_path) -> None:
    out = tmp_path / "operation.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "real-mutation",
            "operation-spec",
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["launch_allowed"] is False
    assert any(item["operation_name"] == "launch_one_instance" for item in payload["operations"])


def test_real_mutation_proposal_cli(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)
    out = tmp_path / "proposal-cli.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "real-mutation",
            "proposal",
            "--m019c-discovery",
            str(refs["discovery"]),
            "--m020-report",
            str(refs["m020"]),
            "--m022-readiness-package",
            str(refs["readiness"]),
            "--real-mutation-absence-audit",
            str(refs["absence"]),
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["boundary_status"] == "review_ready"
    assert payload["launch_allowed"] is False
