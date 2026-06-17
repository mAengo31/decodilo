import json
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_small_fault_matrix_runs_selected_cases(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "fault-matrix",
            "--learners",
            "3",
            "--steps",
            "50",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--cases",
            "learner_kill,syncer_restart",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=40,
    )
    summary = json.loads(completed.stdout)
    assert set(summary["cases"]) == {"learner_kill", "syncer_restart"}
    for result in summary["cases"].values():
        assert result["replay_passed"] is True
        assert result["metric_validation_passed"] is True
