import json
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.soak]


def test_short_local_soak_runs_and_writes_summary(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "soak",
            "--learners",
            "3",
            "--steps",
            "40",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--cases",
            "baseline,slow_restore",
            "--vector-dim",
            "3",
            "--fragments",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )

    summary = json.loads(completed.stdout)
    assert summary["cases_run"] == 2
    assert summary["cases_failed"] == 0
    assert summary["total_committed_sync_rounds"] > 0
    assert summary["total_useful_tokens"] > 0
    assert (tmp_path / "soak_summary.json").exists()
    for path in summary["artifact_paths"]:
        report = json.loads(open(path, encoding="utf-8").read())
        assert report["replay_validation"]["replay_passed"] is True
        assert report["metric_validation"]["passed"] is True
