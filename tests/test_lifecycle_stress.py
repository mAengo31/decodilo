import json
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.lifecycle, pytest.mark.integration, pytest.mark.runtime]


def test_short_lifecycle_stress_cli_runs(tmp_path) -> None:
    out = tmp_path / "lifecycle_stress_report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lifecycle",
            "stress",
            "--workdir",
            str(tmp_path),
            "--learners",
            "2",
            "--steps",
            "40",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--compact-every-rounds",
            "2",
            "--snapshot-every-compactions",
            "1",
            "--gc-plan-every-compactions",
            "1",
            "--cycles",
            "2",
            "--out",
            str(out),
            "--allow-spill-to-disk",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    preflight = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "preflight",
            "local",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0
    assert report["cycles_completed"] == 2
    assert report["compactions_performed"] >= 2
    assert report["genesis_replay_passed"] is True
    assert report["snapshot_replay_passed"] is True
    assert report["artifact_audit_passed"] is True
    assert report["run_validate_passed"] is True
    assert json.loads(preflight.stdout)["preflight_passed"] is True
