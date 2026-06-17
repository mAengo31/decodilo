"""Reusable trainer contract checks for adapter implementations."""

from __future__ import annotations

from decodilo.trainer.interface import TrainerAdapter
from decodilo.trainer.state import TrainerConfig


def assert_basic_trainer_contract(trainer: TrainerAdapter) -> None:
    trainer.initialize(
        run_id="contract-run",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=2,
            learning_rate=0.05,
            throughput_tokens_per_step=10,
            initial_vector=[0.0, 0.0],
            target_vector=[1.0, -1.0],
        ),
    )
    before = trainer.get_full_state()
    result = trainer.train_local_steps(1)
    after = trainer.get_full_state()
    assert result.local_steps == 1
    assert after.local_step == before.local_step + 1
    assert after.tokens_processed > before.tokens_processed
    fragments = trainer.get_state_fragments()
    trainer.apply_global_update(fragments, global_version=after.global_version)
