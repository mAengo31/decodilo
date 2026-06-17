"""Trainer compatibility matrix helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.trainer_runtime_contract import validate_trainer_runtime_contract
from decodilo.trainer.registry import create_trainer
from decodilo.trainer.state import TrainerConfig
from decodilo.trainer.torch_optional import torch_available


class TrainerCompatibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    trainer_name: str
    available: bool
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)
    checks_skipped: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    state_kind: str | None = None
    estimated_state_bytes: int | None = None
    optional_dependency_notes: str | None = None


class TrainerCompatibilityMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: list[TrainerCompatibilityResult]

    @property
    def passed(self) -> bool:
        return all(result.available is False or not result.checks_failed for result in self.results)


def trainer_names(*, include_optional: bool = True) -> list[str]:
    names = ["numpy_convex", "scripted"]
    if include_optional:
        names.extend(["torch_tiny", "torch_causal_lm"])
    return names


def trainer_available(name: str) -> tuple[bool, str | None]:
    if name in {"torch_tiny", "torch_causal_lm"} and not torch_available():
        return False, "optional torch extra is not installed"
    return True, None


def trainer_config_for(name: str) -> TrainerConfig:
    if name == "torch_causal_lm":
        return TrainerConfig(
            vector_dim=estimate_torch_causal_lm_params_for_contract(),
            learning_rate=0.05,
            throughput_tokens_per_step=8,
            vocab_size=16,
            seq_len=6,
            batch_size=2,
            d_model=8,
            num_layers=1,
            num_heads=2,
            mlp_ratio=2.0,
            device="cpu",
        )
    return TrainerConfig(
        vector_dim=4,
        learning_rate=0.05,
        throughput_tokens_per_step=10,
        batch_size=2,
    )


def estimate_torch_causal_lm_params_for_contract() -> int:
    from decodilo.trainer.torch_causal_lm import estimate_causal_lm_num_parameters

    return estimate_causal_lm_num_parameters(
        vocab_size=16,
        seq_len=6,
        d_model=8,
        num_layers=1,
        mlp_ratio=2.0,
    )


def check_trainer_compatibility(name: str) -> TrainerCompatibilityResult:
    available, note = trainer_available(name)
    if not available:
        return TrainerCompatibilityResult(
            trainer_name=name,
            available=False,
            checks_skipped=["all"],
            optional_dependency_notes=note,
        )
    trainer = create_trainer(name)
    config = trainer_config_for(name)
    result = validate_trainer_runtime_contract(trainer, config=config)
    checks = [
        "initialize",
        "train_local_steps",
        "nonnegative_tokens",
        "state_export",
        "fragment_roundtrip",
        "apply_global_update",
        "checkpoint_restore",
        "estimate_state_bytes",
        "health",
    ]
    state_kind = None
    estimated_state_bytes = None
    if result.passed:
        state = trainer.get_full_state()
        state_kind = state.trainer_state_kind
        estimated_state_bytes = trainer.estimate_state_bytes()
        if getattr(trainer, "evaluate", None) is not None:
            trainer.evaluate(eval_steps=1)
            checks.append("eval")
    return TrainerCompatibilityResult(
        trainer_name=name,
        available=True,
        checks_passed=checks if result.passed else [],
        checks_failed=[] if result.passed else checks,
        errors=result.errors,
        state_kind=state_kind,
        estimated_state_bytes=estimated_state_bytes,
    )


def build_trainer_compatibility_matrix(
    *,
    include_optional: bool = False,
) -> TrainerCompatibilityMatrix:
    return TrainerCompatibilityMatrix(
        results=[
            check_trainer_compatibility(name)
            for name in trainer_names(include_optional=include_optional)
        ]
    )
