from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_m029_run_help_accepts_m051_bootstrap_flags():
    result = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "lambda", "m029", "run", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--m051-bootstrap-authorization" in result.stdout
    assert "--m051-metadata-plan" in result.stdout
    assert "--m051-bootstrap-execution-gate-check" in result.stdout
    assert "--m051-no-mutation-no-ssh-audit" in result.stdout
    assert "--m051-bootstrap-runbook-preview" in result.stdout
    assert "--m050-report" in result.stdout
    assert "--m051-one-shot-arming" in result.stdout
    assert "--m051-reviewer-bridge" in result.stdout
    assert "--m051-artifact-binding" in result.stdout
    assert "--m051-arming-gate" in result.stdout
