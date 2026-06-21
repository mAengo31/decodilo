import subprocess
import sys

import pytest


def test_pytest_markers_are_configured(pytestconfig) -> None:
    markers = "\n".join(pytestconfig.getini("markers"))

    for marker in (
        "slow",
        "soak",
        "perf",
        "torch_optional",
        "hardware_optional",
        "cloud_disabled",
    ):
        assert marker in markers


def test_at_least_one_soak_and_perf_test_is_marked() -> None:
    assert pytest.MarkDecorator is not None
    assert "pytest.mark.soak" in open("tests/test_soak_profiles.py", encoding="utf-8").read()
    assert "pytest.mark.perf" in open("tests/test_perf_baselines.py", encoding="utf-8").read()


def test_quick_marker_command_runs_cleanly() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_retry_policy.py",
            "-q",
            "-m",
            "not slow and not soak and not perf and not hardware_optional",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0
    assert "passed" in completed.stdout
    assert "PytestUnknownMarkWarning" not in completed.stderr
