import math

import pytest

from decodilo.trainer.state import TrainerConfig
from decodilo.trainer.torch_optional import torch_available

pytestmark = pytest.mark.skipif(
    not torch_available(),
    reason="optional torch extra is not installed",
)
pytestmark = [pytestmark, pytest.mark.torch_optional]


def _config() -> TrainerConfig:
    from decodilo.trainer.torch_causal_lm import estimate_causal_lm_num_parameters

    return TrainerConfig(
        vector_dim=estimate_causal_lm_num_parameters(
            vocab_size=16,
            seq_len=6,
            d_model=8,
            num_layers=1,
        ),
        learning_rate=0.03,
        throughput_tokens_per_step=12,
        vocab_size=16,
        seq_len=6,
        batch_size=2,
        d_model=8,
        num_layers=1,
        num_heads=2,
        device="cpu",
    )


def _trainer(learner_id: str = "learner-0"):
    from decodilo.trainer.torch_causal_lm import TinyTorchCausalLMTrainer

    trainer = TinyTorchCausalLMTrainer()
    trainer.initialize(
        run_id="torch-causal-lm-run",
        learner_id=learner_id,
        seed=123,
        initial_state=None,
        config=_config(),
    )
    return trainer


def test_causal_lm_initializes_and_same_seed_is_deterministic() -> None:
    first = _trainer()
    second = _trainer()

    assert first.health().healthy is True
    assert first.get_full_state().checksum == second.get_full_state().checksum
    assert first.num_parameters == _config().vector_dim


def test_causal_lm_training_changes_parameters_and_returns_finite_metrics() -> None:
    trainer = _trainer()
    before = trainer.get_full_state().checksum

    result = trainer.train_local_steps(2)

    assert result.tokens_processed == 24
    assert result.local_steps_completed == 2
    assert result.final_loss is not None
    assert math.isfinite(result.final_loss)
    assert result.grad_norm is not None
    assert math.isfinite(result.grad_norm)
    assert trainer.get_full_state().checksum != before
    assert trainer.health().nonfinite_detected is False


def test_causal_lm_named_state_export_import_and_eval() -> None:
    trainer = _trainer()
    trainer.train_local_steps(1)
    state = trainer.get_full_state()
    restored = _trainer("learner-1")

    restored.set_full_state(state, global_version=state.global_version)
    eval_result = restored.evaluate(eval_steps=1)

    assert restored.get_full_state().checksum == state.checksum
    assert eval_result.eval_tokens == _config().batch_size * _config().seq_len
    assert math.isfinite(eval_result.eval_loss)


def test_causal_lm_checkpoint_restore_reproduces_state_checksum() -> None:
    trainer = _trainer()
    trainer.train_local_steps(1)
    checkpoint = trainer.checkpoint_payload()
    restored = _trainer("learner-1")

    restored.restore_from_checkpoint(checkpoint)

    assert restored.get_full_state().checksum == trainer.get_full_state().checksum


def test_causal_lm_metadata_records_actual_device_and_cuda_availability() -> None:
    trainer = _trainer()
    metadata = trainer.get_full_state().metadata

    assert metadata["requested_device"] == "cpu"
    assert metadata["actual_device"] == "cpu"
    assert isinstance(metadata["cuda_available"], bool)
