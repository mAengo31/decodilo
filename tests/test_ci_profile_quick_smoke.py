from __future__ import annotations

import os
import subprocess
import sys

from decodilo.runtime.ci_profile_manifest import QUICK_EXPRESSION


def test_quick_profile_collects_representative_fast_suite() -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            QUICK_EXPRESSION,
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "test_lambda_mutation_guard.py" in result.stdout
    assert "test_lambda_lifecycle_smoke_success_record.py" in result.stdout
    assert "test_lambda_m046_fake_server_capacity_selected_flow.py" not in result.stdout
    assert "test_lambda_m039_run_accepts_lower_cost_flags.py" not in result.stdout
