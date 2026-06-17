import pytest

from decodilo.runtime.trainer_runtime_contract import validate_trainer_runtime_contract
from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.scripted import ScriptedTrainer
from decodilo.trainer.state import (
    TrainerConfig,
    TrainerFragment,
    TrainerHealth,
    TrainerState,
    TrainStepResult,
)
from decodilo.trainer.torch_optional import torch_available


def test_numpy_convex_trainer_passes_runtime_contract() -> None:
    result = validate_trainer_runtime_contract(NumpyConvexTrainer())

    assert result.passed, result.errors


def test_scripted_trainer_passes_normal_runtime_contract() -> None:
    result = validate_trainer_runtime_contract(ScriptedTrainer())

    assert result.passed, result.errors


def test_torch_tiny_trainer_passes_contract_when_available() -> None:
    if not torch_available():
        pytest.skip("optional torch extra is not installed")
    from decodilo.trainer.torch_tiny import TinyTorchMLPTrainer

    result = validate_trainer_runtime_contract(TinyTorchMLPTrainer())

    assert result.passed, result.errors


class BadTrainer:
    def initialize(self, **kwargs) -> None:
        pass

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        return TrainStepResult(local_steps=0, tokens_processed=0, tokens_since_last_sync=0)

    def get_state_fragments(self, fragment_ids=None) -> list[TrainerFragment]:
        return []

    def apply_global_update(self, fragments, *, global_version: int) -> None:
        pass

    def get_full_state(self) -> TrainerState:
        raise RuntimeError("bad trainer")

    def set_full_state(self, state: TrainerState, *, global_version: int) -> None:
        pass

    def checkpoint_payload(self) -> dict:
        return {}

    def restore_from_checkpoint(self, payload: dict) -> None:
        pass

    def estimate_state_bytes(self) -> int:
        return 0

    def health(self) -> TrainerHealth:
        raise RuntimeError("bad trainer")


def test_runtime_contract_rejects_bad_trainer() -> None:
    result = validate_trainer_runtime_contract(
        BadTrainer(),
        config=TrainerConfig(vector_dim=2, learning_rate=0.0, throughput_tokens_per_step=0),
    )

    assert result.passed is False
    assert result.errors
