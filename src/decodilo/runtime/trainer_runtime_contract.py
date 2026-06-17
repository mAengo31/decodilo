"""Runtime contract checks for trainer adapters."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.errors import InvariantViolation
from decodilo.trainer.interface import TrainerAdapter
from decodilo.trainer.registry import create_trainer
from decodilo.trainer.state import TrainerConfig
from decodilo.trainer.state_codec import validate_fragment, validate_state


@dataclass(frozen=True)
class TrainerContractResult:
    passed: bool
    errors: list[str]


def validate_trainer_runtime_contract(
    trainer: TrainerAdapter,
    *,
    run_id: str = "contract-run",
    learner_id: str = "learner-0",
    seed: int = 123,
    config: TrainerConfig | None = None,
    expect_checksum_change: bool = True,
) -> TrainerContractResult:
    """Run local runtime assumptions against a trainer adapter."""

    errors: list[str] = []
    cfg = config or TrainerConfig(
        vector_dim=4,
        learning_rate=0.05,
        throughput_tokens_per_step=10,
        batch_size=2,
    )
    try:
        trainer.initialize(
            run_id=run_id,
            learner_id=learner_id,
            seed=seed,
            initial_state=None,
            config=cfg,
        )
        before = trainer.get_full_state()
        validate_state(before)
        before_health = trainer.health()
        result = trainer.train_local_steps(1)
        after = trainer.get_full_state()
        validate_state(after)
        after_health = trainer.health()
        if result.tokens_processed < 0:
            errors.append("train_local_steps returned negative tokens")
        if after.local_step < before.local_step:
            errors.append("local_step moved backwards")
        if after.tokens_processed < before.tokens_processed:
            errors.append("tokens_processed moved backwards")
        if (
            expect_checksum_change
            and result.tokens_processed > 0
            and before.checksum == after.checksum
        ):
            errors.append("state checksum did not change after nonzero training")
        fragments = trainer.get_state_fragments()
        if not fragments:
            errors.append("trainer returned no fragments")
        for fragment in fragments:
            validate_fragment(fragment)
        if trainer.estimate_state_bytes() <= 0:
            errors.append("trainer estimated non-positive state bytes")
        checkpoint = trainer.checkpoint_payload()
        restored = create_trainer(after.trainer_type)
        restored.initialize(
            run_id=run_id,
            learner_id=learner_id,
            seed=seed,
            initial_state=None,
            config=cfg,
        )
        restored.restore_from_checkpoint(checkpoint)
        restored_state = restored.get_full_state()
        if restored_state.checksum != after.checksum:
            errors.append("checkpoint restore did not preserve state checksum")
        trainer.apply_global_update(fragments, global_version=after.global_version + 1)
        applied = trainer.health()
        if applied.global_version != after.global_version + 1:
            errors.append("apply_global_update did not set global version")
        if after_health.local_step < before_health.local_step:
            errors.append("health local_step moved backwards")
    except Exception as exc:  # noqa: BLE001 - report contract failures uniformly
        errors.append(f"{exc.__class__.__name__}: {exc}")
    return TrainerContractResult(passed=not errors, errors=errors)


def require_trainer_runtime_contract(trainer: TrainerAdapter, **kwargs) -> None:
    result = validate_trainer_runtime_contract(trainer, **kwargs)
    if not result.passed:
        raise InvariantViolation("; ".join(result.errors))
