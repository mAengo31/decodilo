"""Trainer adapter boundary for local learner workers."""

from decodilo.trainer.flattening import FlatFragment, FlatState, FragmentLayout
from decodilo.trainer.interface import TrainerAdapter
from decodilo.trainer.named_state import NamedTensorState
from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.registry import create_trainer
from decodilo.trainer.state import (
    TrainerConfig,
    TrainerFragment,
    TrainerHealth,
    TrainerState,
    TrainStepResult,
)
from decodilo.trainer.tensor_manifest import (
    FragmentCodecMetadata,
    TensorManifest,
    TensorSpec,
)
from decodilo.trainer.torch_optional import torch_available

__all__ = [
    "FlatFragment",
    "FlatState",
    "FragmentCodecMetadata",
    "FragmentLayout",
    "NamedTensorState",
    "NumpyConvexTrainer",
    "TensorManifest",
    "TensorSpec",
    "TrainerAdapter",
    "TrainerConfig",
    "TrainerFragment",
    "TrainerHealth",
    "TrainerState",
    "TrainStepResult",
    "create_trainer",
    "torch_available",
]
