import json
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_validate_report_cli_passes_and_fails_tampered_report(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "25",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "local", "validate-report", str(report_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["metrics"]["wasted_tokens"] = -1
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(report), encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "local", "validate-report", str(tampered)],
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1
