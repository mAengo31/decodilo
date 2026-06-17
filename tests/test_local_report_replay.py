import json
import subprocess
import sys

import pytest

from decodilo.syncer.replay import replay_event_log

pytestmark = [pytest.mark.integration, pytest.mark.runtime, pytest.mark.replay]


def test_local_report_schema_and_replay(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "3",
            "--steps",
            "60",
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
    replayed = replay_event_log(report["event_log_path"])

    assert report["run_id"]
    assert report["mode"] == "local_multiprocess"
    assert report["replay_validation"]["replay_passed"] is True
    assert (
        report["replay_validation"]["replay_final_global_version"]
        == report["final_global_version"]
    )
    assert replayed.accepted_useful_tokens == report["metrics"]["useful_tokens_accepted"]
    assert report["process_summary"]["exit_codes"]
    assert report["learner_logs"]


def test_local_quorum_failure_skips_without_invalid_commit(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "3",
            "--steps",
            "90",
            "--min-quorum",
            "3",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--kill-learner",
            "learner-0:after-round=1",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["metrics"]["committed_sync_rounds"] >= 1
    assert report["metrics"]["skipped_sync_rounds"] > 0
    assert report["replay_validation"]["replay_passed"] is True
