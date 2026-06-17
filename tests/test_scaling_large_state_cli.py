import json
import subprocess
import sys


def _run_large_state(*, memory_budget_mb: int) -> dict:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "large-state",
            "--params",
            "7000000000",
            "--bytes-per-param",
            "2",
            "--optimizer-multiplier",
            "2",
            "--chunk-size-mb",
            "64",
            "--memory-budget-mb",
            str(memory_budget_mb),
            "--learners",
            "8",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return json.loads(completed.stdout)


def test_large_state_scaling_cli_reports_required_arithmetic() -> None:
    output = _run_large_state(memory_budget_mb=1024)

    assert output["parameter_count"] == 7_000_000_000
    assert output["parameter_bytes"] == 14_000_000_000
    assert output["optimizer_multiplier"] == 2
    assert output["optimizer_state_bytes"] == 28_000_000_000
    assert output["total_state_bytes"] == 42_000_000_000
    assert output["chunk_size_bytes"] == 64 * 1024 * 1024
    assert output["estimated_chunk_count"] == 626
    assert output["memory_budget_bytes"] == 1024 * 1024 * 1024
    assert output["fits_in_memory"] is False
    assert output["spill_required"] is True
    assert output["learners"] == 8
    assert output["warnings"]


def test_large_state_scaling_memory_budget_changes_fit_decision() -> None:
    small = _run_large_state(memory_budget_mb=1024)
    large = _run_large_state(memory_budget_mb=50_000)

    assert small["fits_in_memory"] is False
    assert small["spill_required"] is True
    assert large["fits_in_memory"] is True
    assert large["spill_required"] is False


def test_malformed_large_state_flag_is_rejected() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "large-state",
            "--params",
            "7000000000",
            "--bytes-per-param",
            "2",
            "--optimizer-multiplier-size-mb",
            "64",
            "--chunk-size-mb",
            "64",
            "--memory-budget-mb",
            "1024",
            "--learners",
            "8",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "unrecognized arguments" in completed.stderr or "required" in completed.stderr
