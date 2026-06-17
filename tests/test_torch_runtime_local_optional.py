import json
import subprocess
import sys

import pytest

from decodilo.trainer.torch_optional import torch_available

pytestmark = [
    pytest.mark.skipif(
        not torch_available(),
        reason="optional torch extra is not installed",
    ),
    pytest.mark.torch_optional,
    pytest.mark.integration,
    pytest.mark.runtime,
]


def test_torch_causal_lm_runs_short_local_runtime(tmp_path) -> None:
    config_json = json.dumps(
        {
            "vocab_size": 16,
            "seq_len": 4,
            "batch_size": 1,
            "d_model": 4,
            "num_layers": 0,
            "num_heads": 1,
            "learning_rate": 0.05,
            "device": "cpu",
        },
        sort_keys=True,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--trainer",
            "torch_causal_lm",
            "--learners",
            "1",
            "--steps",
            "2",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
            "--local-steps-per-sync",
            "1",
            "--fragments",
            "1",
            "--heartbeat-timeout-seconds",
            "2",
            "--trainer-config-json",
            config_json,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    summary = json.loads(completed.stdout)
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert summary["replay_passed"] is True
    assert report["trainer_type"] == "torch_causal_lm"
    assert report["trainer_state_kind"] == "named_tensors"
    assert report["trainer_state_bytes_estimate"] > 0
    assert report["trainer_nonfinite_detected"] is False
