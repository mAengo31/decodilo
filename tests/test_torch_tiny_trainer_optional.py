import pytest

from decodilo.trainer.state import TrainerConfig
from decodilo.trainer.torch_optional import torch_available

pytestmark = pytest.mark.skipif(
    not torch_available(),
    reason="optional torch extra is not installed",
)


def _trainer():
    from decodilo.trainer.torch_tiny import TinyTorchMLPTrainer

    trainer = TinyTorchMLPTrainer()
    trainer.initialize(
        run_id="torch-run",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=4,
            learning_rate=0.01,
            throughput_tokens_per_step=8,
            batch_size=2,
            device="cpu",
        ),
    )
    return trainer


def test_tiny_torch_trainer_initializes_and_trains_on_cpu() -> None:
    trainer = _trainer()
    before = trainer.get_full_state()
    result = trainer.train_local_steps(2)
    after = trainer.get_full_state()

    assert result.tokens_processed == 16
    assert result.loss is not None
    assert result.loss == pytest.approx(result.loss)
    assert before.checksum != after.checksum
    assert after.trainer_state_kind == "named_tensors"


def test_tiny_torch_same_seed_same_initial_state_and_checkpoint_roundtrip() -> None:
    first = _trainer()
    second = _trainer()
    assert first.get_full_state().checksum == second.get_full_state().checksum

    first.train_local_steps(1)
    checkpoint = first.checkpoint_payload()
    restored = _trainer()
    restored.restore_from_checkpoint(checkpoint)
    assert restored.get_full_state().checksum == first.get_full_state().checksum


def test_tiny_torch_named_state_export_import_roundtrip() -> None:
    trainer = _trainer()
    trainer.train_local_steps(1)
    fragment = trainer.get_state_fragments()[0]
    trainer.apply_global_update([fragment], global_version=1)

    assert trainer.health().global_version == 1
    assert fragment.trainer_state_kind == "named_tensors"
