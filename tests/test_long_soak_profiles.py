import json
import subprocess
import sys

import pytest

from decodilo.runtime.soak_profiles import get_soak_profile


def test_long_profiles_require_long_flag(tmp_path) -> None:
    assert get_soak_profile("local_long_lifecycle").requires_long is True
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "local_long_lifecycle",
            "--workdir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "requires --long" in completed.stdout


@pytest.mark.soak
@pytest.mark.integration
def test_lifecycle_ci_soak_profile_passes(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "lifecycle_ci",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=50,
    )
    summary = json.loads(completed.stdout)
    assert summary["cases_failed"] == 0
    assert summary["lifecycle_cycles"] == 1
    assert summary["compactions"] >= 1


@pytest.mark.soak
@pytest.mark.perf
@pytest.mark.integration
def test_binary_perf_ci_soak_profile_passes(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "binary_perf_ci",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    summary = json.loads(completed.stdout)
    assert summary["cases_failed"] == 0
    assert summary["perf_reports"]

