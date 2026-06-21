from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_m039_run_help_accepts_lower_cost_flags():
    result = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "lambda", "m029", "run", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--m039-authorization" in result.stdout
    assert "--lower-cost-canonical-readiness" in result.stdout
    assert "--response-loss-controls" in result.stdout
    assert "--lower-cost-launch-plan" in result.stdout
    assert "--ssh-key-selection" in result.stdout
