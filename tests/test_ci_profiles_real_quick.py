import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


def test_marker_summary_command_works() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "dev", "test-profile-summary"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "not slow and not soak and not perf and not integration" in completed.stdout


def test_quick_command_deselects_substantially_more_than_seven_tests() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_soak_profiles.py",
            "tests/test_local_multiprocess_smoke.py",
            "tests/test_local_process_failure.py",
            "tests/test_binary_global_update_delivery.py",
            "tests/test_binary_chunked_checkpoint_recovery.py",
            "tests/test_retry_policy.py",
            "-q",
            "-m",
            "not slow and not soak and not perf and not integration",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "deselected" in completed.stdout
    deselected = int(completed.stdout.split(" deselected")[0].split()[-1])
    assert deselected > 7
