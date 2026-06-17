import pytest

from decodilo.trainer.torch_optional import torch_available

pytestmark = pytest.mark.skipif(
    not torch_available(),
    reason="optional torch extra is not installed",
)


def test_causal_lm_checkpoint_resume_keeps_synthetic_stream_position() -> None:
    from decodilo.trainer.state import TrainerConfig
    from decodilo.trainer.torch_causal_lm import TinyTorchCausalLMTrainer

    config = TrainerConfig(
        vector_dim=152,
        learning_rate=0.05,
        throughput_tokens_per_step=4,
        vocab_size=16,
        seq_len=4,
        batch_size=1,
        d_model=4,
        num_layers=0,
        num_heads=1,
        device="cpu",
    )
    trainer = TinyTorchCausalLMTrainer()
    trainer.initialize(
        run_id="resume",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=config,
    )
    trainer.train_local_steps(2)
    checkpoint = trainer.checkpoint_payload()
    restored = TinyTorchCausalLMTrainer()
    restored.initialize(
        run_id="resume",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=config,
    )

    restored.restore_from_checkpoint(checkpoint)
    restored.train_local_steps(1)

    assert restored.local_step == 3
    assert restored.tokens_processed == 12
    assert restored.health().healthy is True

