from __future__ import annotations

import json
import subprocess
import sys

import pytest

from decodilo.operation import OperationSpec
from decodilo.trainer.torch_causal_lm import estimate_causal_lm_num_parameters
from decodilo.trainer.torch_optional import torch_available


def test_operation_spec_torch_causal_lm_profile_computes_vector_dim() -> None:
    spec = OperationSpec.torch_causal_lm_profile(
        name="gpu-causal-lm-profile",
        learners=2,
        min_quorum=2,
        steps=8,
        device="cuda",
        vocab_size=32,
        seq_len=8,
        batch_size=2,
        d_model=16,
        num_layers=1,
        num_heads=2,
        learning_rate=0.001,
    )

    assert spec.name == "gpu-causal-lm-profile"
    assert spec.trainer_type == "torch_causal_lm"
    assert spec.inner_optimizer == "adamw"
    assert spec.outer_optimizer == "nesterov"
    assert spec.trainer_config["optimizer"] == "adamw"
    assert spec.trainer_config["device"] == "cuda"
    assert spec.trainer_config["real_model_training_claimed"] is True
    assert spec.trainer_config["paper_scale_training_claimed"] is False
    assert spec.vector_dim == estimate_causal_lm_num_parameters(
        vocab_size=32,
        seq_len=8,
        d_model=16,
        num_layers=1,
    )


def test_operation_spec_rejects_torch_profile_without_adamw() -> None:
    with pytest.raises(ValueError, match="torch_causal_lm operation requires AdamW"):
        OperationSpec(
            trainer_type="torch_causal_lm",
            inner_optimizer="adamw",
            trainer_config={"optimizer": "sgd", "device": "cpu"},
            vector_dim=estimate_causal_lm_num_parameters(),
        )


@pytest.mark.skipif(not torch_available(), reason="optional torch extra is not installed")
def test_torch_causal_lm_operation_profile_runs_local_cpu_runtime(tmp_path) -> None:
    spec = OperationSpec.torch_causal_lm_profile(
        name="cpu-causal-lm-profile",
        learners=1,
        min_quorum=1,
        steps=2,
        device="cpu",
        vocab_size=16,
        seq_len=4,
        batch_size=1,
        d_model=4,
        num_layers=0,
        num_heads=1,
        learning_rate=0.01,
    )
    report_path = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--trainer",
            spec.trainer_type,
            "--trainer-config-json",
            json.dumps(spec.trainer_config, sort_keys=True),
            "--outer-optimizer",
            spec.outer_optimizer,
            "--outer-lr",
            str(spec.outer_lr),
            "--learners",
            str(spec.learners),
            "--steps",
            str(spec.steps),
            "--min-quorum",
            str(spec.min_quorum),
            "--seed",
            str(spec.seed),
            "--vector-dim",
            str(spec.vector_dim),
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--local-steps-per-sync",
            str(spec.local_steps_per_sync),
            "--fragments",
            str(spec.fragments),
            "--heartbeat-timeout-seconds",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert completed.returncode == 0
    assert report["trainer_type"] == "torch_causal_lm"
    assert report["trainer_state_kind"] == "named_tensors"
    assert report["metrics"]["inner_optimizer_semantics"] == "adamw"
    assert report["metrics"]["outer_optimizer_semantics"] == "nesterov"
    assert report["metrics"]["real_training_mechanics_exercised"] is True
    assert report["metrics"]["real_model_training_claimed"] is True
    assert report["metrics"]["paper_scale_training_claimed"] is False
    assert report["trainer_num_parameters"] == spec.vector_dim
    assert report["replay_validation"]["replay_passed"] is True
