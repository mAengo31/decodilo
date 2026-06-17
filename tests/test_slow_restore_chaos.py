import json
import subprocess
import sys

import numpy as np
import pytest

from decodilo.learner.fake_learner import FakeLearner
from decodilo.learner.learner_state import LearnerState
from decodilo.protocol.messages import LearnerStatus

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_slow_and_restore_change_synthetic_throughput() -> None:
    learner = FakeLearner(
        LearnerState(
            learner_id="learner-1",
            local_step=0,
            tokens_processed=0,
            parameters=np.array([0.0]),
            last_global_version_seen=0,
            status=LearnerStatus.ALIVE,
            throughput_tokens_per_step=100,
        ),
        learning_rate=0.0,
    )

    learner.slow(0.25)
    for _ in range(8):
        learner.tick(target_vector=np.array([0.0]))
    slowed_tokens = learner.state.tokens_processed
    learner.restore_speed()
    for _ in range(8):
        learner.tick(target_vector=np.array([0.0]))

    assert slowed_tokens == 50
    assert learner.state.tokens_processed == 850


def test_local_slow_restore_chaos_records_events_and_replay_passes(tmp_path) -> None:
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
            "140",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--slow-learner",
            "learner-1:factor=0.25:after-round=1",
            "--restore-learner",
            "learner-1:after-round=3",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=25,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8")

    assert "learner-1" in report["process_summary"]["slowed_learners"]
    assert "learner-1" in report["process_summary"]["restored_learners"]
    assert "learner_slowed" in events
    assert "learner_speed_restored" in events
    assert report["metrics"]["committed_sync_rounds"] > 3
    assert report["replay_validation"]["replay_passed"] is True
