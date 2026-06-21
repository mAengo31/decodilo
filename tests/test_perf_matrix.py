import json
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_perf_matrix_dry_run_and_max_cases(tmp_path) -> None:
    out = tmp_path / "matrix.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "matrix",
            "--workdir",
            str(tmp_path / "matrix"),
            "--learners",
            "1,2",
            "--elements",
            "4",
            "--chunk-size-kb",
            "64",
            "--out",
            str(out),
            "--dry-run",
            "--max-cases",
            "4",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["dry_run"] is True
    assert payload["cases_requested"] == 2

    failed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "matrix",
            "--workdir",
            str(tmp_path / "matrix2"),
            "--learners",
            "1,2",
            "--elements",
            "4,8",
            "--chunk-size-kb",
            "64",
            "--out",
            str(tmp_path / "too_many.json"),
            "--dry-run",
            "--max-cases",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert failed.returncode != 0
    assert "max-cases" in failed.stderr


@pytest.mark.perf
@pytest.mark.integration
def test_perf_matrix_small_run(tmp_path) -> None:
    out = tmp_path / "matrix.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "matrix",
            "--workdir",
            str(tmp_path / "matrix"),
            "--learners",
            "1",
            "--elements",
            "4",
            "--chunk-size-kb",
            "64",
            "--steps",
            "20",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=40,
    )
    payload = json.loads(completed.stdout)
    assert payload["cases_requested"] == 1
    assert payload["cases_failed"] == 0
    assert json.loads(out.read_text(encoding="utf-8"))["cases_completed"] == 1
