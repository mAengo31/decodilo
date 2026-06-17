import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.runtime, pytest.mark.slow]


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_short_local_stress_with_syncer_restart(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "6",
            "--steps",
            "80",
            "--min-quorum",
            "3",
            "--seed",
            "321",
            "--vector-dim",
            "3",
            "--fragments",
            "3",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--syncer-checkpoint-interval-rounds",
            "1",
            "--restart-syncer-after-round",
            "2",
            "--slow-learner",
            "learner-1:factor=0.5:after-round=1",
            "--restore-learner",
            "learner-1:after-round=3",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=35,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["metrics"]["committed_sync_rounds"] > 0
    assert report["metrics"]["useful_tokens_accepted"] > 0
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    for pids in report["process_summary"]["learner_pids"].values():
        for pid in pids:
            assert not _pid_alive(pid)
