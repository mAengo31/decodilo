import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_local_multiprocess_smoke(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "3",
            "--steps",
            "80",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert completed.returncode == 0
    assert report["mode"] == "local_multiprocess"
    assert report["metrics"]["committed_sync_rounds"] > 0
    assert report["metrics"]["useful_tokens_accepted"] > 0
    assert report["replay_validation"]["replay_passed"] is True
    for pids in report["process_summary"]["learner_pids"].values():
        for pid in pids:
            assert not _pid_alive(pid)
    assert not _pid_alive(report["process_summary"]["syncer_pid"])
