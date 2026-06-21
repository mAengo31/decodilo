from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_m046_run_help_accepts_capacity_selected_flags():
    result = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "lambda", "m029", "run", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--capacity-selected-m046-authorization" in result.stdout
    assert "--capacity-selected-cost-risk-review" in result.stdout
    assert "--capacity-selected-operator-approval" in result.stdout
    assert "--capacity-selected-gate-check" in result.stdout
    assert "--capacity-aware-selector-output" in result.stdout
    assert "--capacity-aware-selector-authorization" in result.stdout
    assert "--capacity-aware-selector-gate-check" in result.stdout
    assert "--capacity-history" in result.stdout
    assert "--capacity-retry-policy" in result.stdout
    assert "--m045-report" in result.stdout
