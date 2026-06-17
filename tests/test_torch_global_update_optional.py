import pytest

from decodilo.trainer.torch_optional import torch_available

pytestmark = pytest.mark.skipif(
    not torch_available(),
    reason="optional torch extra is not installed",
)


def _trainer(seed: int, learner_id: str):
    from decodilo.trainer.state import TrainerConfig
    from decodilo.trainer.torch_causal_lm import TinyTorchCausalLMTrainer

    trainer = TinyTorchCausalLMTrainer()
    trainer.initialize(
        run_id="global-update",
        learner_id=learner_id,
        seed=seed,
        initial_state=None,
        config=TrainerConfig(
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
        ),
    )
    return trainer


def test_global_update_loads_parameters_sets_version_and_resets_optimizer() -> None:
    donor = _trainer(123, "learner-0")
    receiver = _trainer(456, "learner-1")
    donor.train_local_steps(1)
    before = receiver.get_full_state().checksum

    receiver.apply_global_update(donor.get_state_fragments(), global_version=3)

    assert receiver.health().global_version == 3
    assert receiver.last_applied_global_version == 3
    assert receiver.get_full_state().checksum != before
    assert receiver.optimizer_policy.reset_on_global_update is True

