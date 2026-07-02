import json
import subprocess
import sys

import pytest
from helpers.subprocess_retry import run_bounded_subprocess_retry

pytestmark = [
    pytest.mark.integration,
    pytest.mark.runtime,
    pytest.mark.runtime_local,
    pytest.mark.subprocess_heavy,
]


def _run_local(tmp_path, *extra_args):
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "4",
            "--steps",
            "100",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            *extra_args,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return json.loads(report_path.read_text(encoding="utf-8"))


def test_local_process_failure_continues_with_quorum(tmp_path) -> None:
    report = _run_local(tmp_path, "--kill-learner", "learner-0:after-round=2")
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8")

    assert "learner-0" in report["process_summary"]["killed_learners"]
    assert report["metrics"]["committed_sync_rounds"] > 2
    assert report["metrics"]["useful_tokens_accepted"] > 0
    assert "learner_unhealthy" in events
    assert report["replay_validation"]["replay_passed"] is True


def test_local_recovery_after_kill(tmp_path) -> None:
    def run_attempt(attempt_dir):
        report = _run_local(
            attempt_dir,
            "--steps",
            "300",
            "--kill-learner",
            "learner-0:after-round=2",
            "--restart-learner",
            "learner-0:after-round=2",
        )
        records = [
            json.loads(line)
            for line in (attempt_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        recovered = [
            event
            for event in records
            if event["event_type"] == "learner_recovered" and event["learner_id"] == "learner-0"
        ]
        later_accept = [
            event
            for event in records
            if event["event_type"] == "sync_round_committed"
            and "learner-0" in event["payload"]["accepted_learner_ids"]
            and event["sequence"] > recovered[0]["sequence"]
        ]

        assert "learner-0" in report["process_summary"]["restarted_learners"]
        assert recovered
        assert "recovery_version" in recovered[0]["payload"]
        assert later_accept, "restarted learner did not contribute to a post-recovery commit"
        assert report["replay_validation"]["replay_passed"] is True
        return report

    report, retry_report = run_bounded_subprocess_retry(
        label="test_local_recovery_after_kill",
        reason=(
            "subprocess scheduling can delay the restarted learner until peer processes have exited"
        ),
        attempts=3,
        base_tmp_path=tmp_path,
        run_attempt=run_attempt,
    )
    (tmp_path / "subprocess_retry_report.json").write_text(
        retry_report.to_json(),
        encoding="utf-8",
    )
    assert report["replay_validation"]["replay_passed"] is True
