import numpy as np

from decodilo.sim.fake_model import convex_loss
from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.state import TrainerConfig
from decodilo.trainer.state_codec import decode_state


def _trainer(seed: int = 123) -> NumpyConvexTrainer:
    trainer = NumpyConvexTrainer()
    trainer.initialize(
        run_id="run-trainer",
        learner_id="learner-0",
        seed=seed,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=2,
            learning_rate=0.1,
            throughput_tokens_per_step=10,
            initial_vector=[0.0, 0.0],
            target_vector=[1.0, -1.0],
        ),
    )
    return trainer


def test_numpy_convex_trainer_improves_loss() -> None:
    trainer = _trainer()
    before = convex_loss(np.asarray(trainer.get_full_state().parameters), np.array([1.0, -1.0]))

    trainer.train_local_steps(10)

    after = convex_loss(np.asarray(trainer.get_full_state().parameters), np.array([1.0, -1.0]))
    assert after < before
    assert trainer.health().tokens_processed == 100


def test_same_seed_config_produces_identical_state_and_checkpoint_restore() -> None:
    first = _trainer()
    second = _trainer()
    first.train_local_steps(3)
    second.train_local_steps(3)

    assert first.get_full_state() == second.get_full_state()
    restored = NumpyConvexTrainer()
    restored.restore_from_checkpoint(first.checkpoint_payload())
    assert restored.get_full_state() == first.get_full_state()


def test_apply_global_update_changes_state_and_version() -> None:
    trainer = _trainer()
    fragment = trainer.get_state_fragments()[0].model_copy(
        update={"data": [5.0, 6.0], "global_version": 3}
    )

    trainer.apply_global_update([fragment], global_version=3)

    state = trainer.get_full_state()
    assert state.global_version == 3
    assert state.parameters == [5.0, 6.0]
    assert decode_state(trainer.checkpoint_payload()["trainer_state"]) == state
