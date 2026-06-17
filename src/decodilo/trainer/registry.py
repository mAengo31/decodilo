"""Trainer adapter registry."""

from __future__ import annotations

from decodilo.trainer.interface import TrainerAdapter
from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.scripted import ScriptedTrainer


def create_trainer(trainer_type: str) -> TrainerAdapter:
    if trainer_type == "numpy_convex":
        return NumpyConvexTrainer()
    if trainer_type == "scripted":
        return ScriptedTrainer()
    if trainer_type == "torch_tiny":
        from decodilo.trainer.torch_tiny import TinyTorchMLPTrainer

        return TinyTorchMLPTrainer()
    if trainer_type == "torch_causal_lm":
        from decodilo.trainer.torch_causal_lm import TinyTorchCausalLMTrainer

        return TinyTorchCausalLMTrainer()
    raise ValueError(f"unknown trainer_type {trainer_type!r}")
