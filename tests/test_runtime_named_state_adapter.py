import json
import subprocess
import sys
from pathlib import Path

import pytest

from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.state import TrainerConfig


def test_numpy_convex_trainer_exports_named_state_fragments() -> None:
    trainer = NumpyConvexTrainer()
    trainer.initialize(
        run_id="named-run",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=3,
            learning_rate=0.05,
            throughput_tokens_per_step=10,
        ),
    )
    trainer.train_local_steps(1)
    state = trainer.get_full_state()
    fragment = trainer.get_state_fragments()[0]

    assert state.trainer_state_kind == "named_tensors"
    assert state.tensor_manifest is not None
    assert state.tensor_manifest["tensors"][0]["name"] == "weights"
    assert fragment.trainer_state_kind == "named_tensors"
    assert fragment.flat_fragment is not None


@pytest.mark.integration
def test_local_runtime_uses_named_state_path(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "30",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--vector-dim",
            "3",
            "--fragments",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert json.loads(completed.stdout)["replay_passed"] is True
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["trainer_state_kind"] == "named_tensors"
    assert report["replay_validation"]["replay_passed"] is True


def test_syncer_runtime_does_not_import_torch() -> None:
    source = Path("src/decodilo/runtime/syncer_service.py").read_text(encoding="utf-8")

    assert "torch" not in source
    assert "torch_tiny" not in source
