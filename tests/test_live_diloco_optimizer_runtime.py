import json
import subprocess
import sys

import numpy as np

from decodilo.syncer.outer_optimizer import NesterovOuterOptimizer
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge
from decodilo.trainer.registry import create_trainer
from decodilo.trainer.state import TrainerConfig


def test_nesterov_outer_optimizer_matches_diloco_reference_step() -> None:
    initial = np.array([1.0, -2.0, 0.5], dtype=np.float64)
    post_inner = np.array(
        [0.9899000009999999, -1.9898000005, 0.4899500019999996],
        dtype=np.float64,
    )

    result = token_weighted_merge(
        initial,
        [
            LearnerDelta(
                learner_id="learner-0",
                vector=post_inner,
                tokens=21,
                global_version_seen=0,
            )
        ],
        optimizer=NesterovOuterOptimizer(outer_lr=0.5, momentum=0.9),
    )

    np.testing.assert_allclose(
        result.new_global_vector,
        np.array([0.9904050009499998, -1.990310000475, 0.4904525018999996]),
        rtol=0.0,
        atol=1e-12,
    )


def test_tiny_adamw_trainer_runs_real_inner_optimizer_step() -> None:
    trainer = create_trainer("tiny_adamw")
    trainer.initialize(
        run_id="run-live-diloco",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=3,
            learning_rate=0.01,
            throughput_tokens_per_step=21,
            initial_vector=[1.0, -2.0, 0.5],
            target_vector=[0.0, 0.0, 0.0],
            optimizer="adamw",
        ),
    )

    result = trainer.train_local_steps(1)
    state = trainer.get_full_state()

    assert result.local_steps == 1
    assert result.tokens_processed == 21
    assert state.metadata["optimizer"] == "adamw"
    assert state.metadata["optimizer_state"]["step"] == 1
    assert state.metadata["real_training_mechanics_exercised"] is True
    assert state.parameters != [1.0, -2.0, 0.5]


def test_local_runtime_runs_tiny_adamw_inner_and_nesterov_outer(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--trainer",
            "tiny_adamw",
            "--trainer-config-json",
            json.dumps({"optimizer": "adamw"}, sort_keys=True),
            "--outer-optimizer",
            "nesterov",
            "--outer-lr",
            "0.5",
            "--learners",
            "2",
            "--steps",
            "2",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--local-steps-per-sync",
            "1",
            "--fragments",
            "1",
            "--heartbeat-timeout-seconds",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert completed.returncode == 0
    assert report["trainer_type"] == "tiny_adamw"
    assert report["config"]["outer_optimizer"] == "nesterov"
    assert report["metrics"]["outer_optimizer"] == "nesterov"
    assert report["metrics"]["outer_momentum"] == 0.9
    assert report["trainer_config"]["optimizer"] == "adamw"
    assert report["trainer_state_kind"] == "named_tensors"
    assert report["trainer_final_loss"] is not None
    assert report["replay_validation"]["replay_passed"] is True

    # Inner/outer DiLoCo optimizer semantics surfaced by the live runtime.
    assert report["metrics"]["inner_optimizer_semantics"] == "adamw"
    assert report["metrics"]["outer_optimizer_semantics"] == "nesterov"

    # Real (tiny) training mechanics were exercised without overclaiming scale.
    assert report["metrics"]["training_attempted"] is True
    assert report["metrics"]["real_training_mechanics_exercised"] is True
    assert report["metrics"]["real_model_training_claimed"] is False
    assert report["metrics"]["paper_scale_training_claimed"] is False

    # Optimizer state is present and Nesterov/pseudo-gradient evidence is honest.
    assert report["metrics"]["optimizer_state_present"] is True
    assert report["metrics"]["outer_optimizer_semantics_checked"] is True
    assert report["metrics"]["nesterov_outer_optimizer_exercised"] is True
    assert report["metrics"]["pseudo_gradient_numeric_check_passed"] is True
    assert report["metrics"]["pseudo_gradient_numeric_check_reason"] is None
    assert report["metrics"]["pseudo_gradient_numeric_rounds_checked"] >= 1
    # Backward-compatible alias is now backed by the numeric check in LocalRunner.
    assert report["metrics"]["pseudo_gradient_check_passed"] is True

    # Two local learners + one syncer actually committed at least one round.
    assert report["mode"] == "local_multiprocess"
    assert len(report["process_summary"]["learner_pids"]) == 2
    assert report["process_summary"]["syncer_pid"] > 0
    assert report["final_global_version"] >= 1

    # Local-only CPU/synthetic path: no GPU/pricing/budget side path was requested.
    assert report["config"]["gpu_type"] is None
    assert report["config"]["gpus_per_instance"] is None
    assert report["config"]["price_snapshot"] is None
    assert report["budget_manifest"] is None

    # Safety envelope: local-only, no remote/billable/launch surface engaged.
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert report["billable_action_performed"] is False
    assert report["remote_backend_enabled"] is False
    assert report["network_scope"] == "localhost_only"
