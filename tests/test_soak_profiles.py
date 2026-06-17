import json
import subprocess
import sys

import pytest

from decodilo.runtime.soak_profiles import get_soak_profile, list_soak_profiles
from decodilo.trainer.torch_optional import torch_available


def test_soak_profile_definitions_validate() -> None:
    profiles = {profile["name"]: profile for profile in list_soak_profiles()}

    assert "ci" in profiles
    assert "chunked_ci" in profiles
    assert "binary_chunked_ci" in profiles
    assert profiles["ci"]["steps"] <= profiles["local_medium"]["steps"]
    assert get_soak_profile("torch_cpu_ci").optional is True
    assert get_soak_profile("chunked_ci").cases == ["baseline", "syncer_restart"]


@pytest.mark.soak
def test_soak_profile_cli_runs_ci_profile(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "ci",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )

    summary = json.loads(completed.stdout)
    assert summary["profile"] == "ci"
    assert summary["trainer"] == "numpy_convex"
    assert summary["cases_failed"] == 0


@pytest.mark.soak
def test_torch_soak_profile_is_explicitly_optional(tmp_path) -> None:
    profile = get_soak_profile("torch_cpu_ci")
    assert profile.optional is True
    if not torch_available():
        return
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "torch_cpu_ci",
            "--workdir",
            str(tmp_path),
            "--trainer-config-json",
            '{"vocab_size":16,"seq_len":4,"batch_size":1,"d_model":4,'
            '"num_layers":0,"num_heads":1,"learning_rate":0.05,"device":"cpu"}',
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert json.loads(completed.stdout)["cases_failed"] == 0


@pytest.mark.soak
def test_chunked_ci_soak_profile_runs(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "chunked_ci",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )

    summary = json.loads(completed.stdout)
    assert summary["profile"] == "chunked_ci"
    assert summary["cases_failed"] == 0
    assert summary["cases"]["syncer_restart"]["replay_passed"] is True


@pytest.mark.soak
def test_binary_chunked_ci_soak_profile_runs(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--profile",
            "binary_chunked_ci",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )

    summary = json.loads(completed.stdout)
    assert summary["profile"] == "binary_chunked_ci"
    assert summary["cases_failed"] == 0
    assert summary["cases"]["syncer_restart"]["replay_passed"] is True
