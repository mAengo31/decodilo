import json
import subprocess
import sys

from decodilo.runtime.preflight import run_local_preflight


def _local_run(tmp_path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "1",
            "--steps",
            "5",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_local_preflight_passes_valid_local_run(tmp_path) -> None:
    _local_run(tmp_path)

    result = run_local_preflight(workdir=tmp_path)

    assert result.passed is True
    assert result.preflight_passed is True
    assert result.artifact_checks_passed is True
    assert result.launch_ready is False
    assert result.launch_allowed is False
    assert result.checked_artifacts


def test_local_preflight_fails_hash_mismatch(tmp_path) -> None:
    _local_run(tmp_path)
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")

    result = run_local_preflight(workdir=tmp_path)

    assert result.passed is False
    assert any("hash mismatch" in error for error in result.errors)


def test_preflight_local_cli_writes_json(tmp_path) -> None:
    _local_run(tmp_path)
    out = tmp_path / "preflight.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "preflight",
            "local",
            "--workdir",
            str(tmp_path),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert json.loads(completed.stdout)["preflight_passed"] is True
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["launch_ready"] is False
    assert written["launch_allowed"] is False
