"""Pure-Python/Numpy tiny AdamW trainer for live local DiLoCo runtime tests."""

from __future__ import annotations

from typing import Any

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.trainer.flattening import (
    flatten_named_state,
    fragment_flat_state,
    make_fragment_layout,
)
from decodilo.trainer.named_state import named_state_from_numpy
from decodilo.trainer.numpy_convex import make_target_vector
from decodilo.trainer.state import (
    TrainerConfig,
    TrainerFragment,
    TrainerHealth,
    TrainerState,
    TrainStepResult,
)
from decodilo.trainer.state_codec import (
    decode_state,
    encode_state,
    make_fragment,
    make_state,
    validate_fragment,
)


class TinyAdamWTrainer:
    """Small deterministic trainer that exercises real AdamW update mechanics."""

    trainer_type = "tiny_adamw"

    def __init__(self) -> None:
        self.run_id = ""
        self.learner_id = ""
        self.global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0
        self.throughput_tokens_per_step = 0
        self.learning_rate = 0.0
        self.beta1 = 0.9
        self.beta2 = 0.999
        self.epsilon = 1e-8
        self.weight_decay = 0.01
        self.parameters = np.zeros(1, dtype=np.float64)
        self.target = np.zeros(1, dtype=np.float64)
        self.optimizer_step = 0
        self.exp_avg = np.zeros(1, dtype=np.float64)
        self.exp_avg_sq = np.zeros(1, dtype=np.float64)
        self.last_loss: float | None = None

    def initialize(
        self,
        *,
        run_id: str,
        learner_id: str,
        seed: int,
        initial_state: TrainerState | None,
        config: TrainerConfig,
    ) -> None:
        if config.optimizer.lower() != "adamw":
            raise InvariantViolation("tiny_adamw trainer requires optimizer='adamw'")
        self.run_id = run_id
        self.learner_id = learner_id
        self.learning_rate = config.learning_rate
        self.throughput_tokens_per_step = config.throughput_tokens_per_step
        self.target = (
            np.asarray(config.target_vector, dtype=np.float64)
            if config.target_vector is not None
            else make_target_vector(config.vector_dim, seed=seed + 1)
        )
        if initial_state is not None:
            self.set_full_state(initial_state, global_version=initial_state.global_version)
            return
        self.parameters = (
            np.asarray(config.initial_vector, dtype=np.float64)
            if config.initial_vector is not None
            else np.zeros(config.vector_dim, dtype=np.float64)
        )
        self.exp_avg = np.zeros_like(self.parameters)
        self.exp_avg_sq = np.zeros_like(self.parameters)
        self.global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0
        self.optimizer_step = 0
        self.last_loss = self._loss()

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        if num_steps < 0:
            raise ValueError("num_steps must be non-negative")
        previous_step = self.local_step
        previous_tokens = self.tokens_processed
        loss_before = self._loss()
        grad_norm = 0.0
        for _ in range(num_steps):
            gradient = self._gradient()
            grad_norm = float(np.linalg.norm(gradient))
            self.optimizer_step += 1
            self.exp_avg = self.beta1 * self.exp_avg + (1.0 - self.beta1) * gradient
            self.exp_avg_sq = self.beta2 * self.exp_avg_sq + (1.0 - self.beta2) * (
                gradient * gradient
            )
            bias_corrected_avg = self.exp_avg / (1.0 - self.beta1**self.optimizer_step)
            bias_corrected_sq = self.exp_avg_sq / (1.0 - self.beta2**self.optimizer_step)
            decayed = self.parameters * (1.0 - self.learning_rate * self.weight_decay)
            self.parameters = decayed - self.learning_rate * bias_corrected_avg / (
                np.sqrt(bias_corrected_sq) + self.epsilon
            )
            self.local_step += 1
            self.tokens_processed += self.throughput_tokens_per_step
            self.tokens_since_last_sync += self.throughput_tokens_per_step
        self.last_loss = self._loss()
        return TrainStepResult(
            local_steps=self.local_step - previous_step,
            local_steps_completed=self.local_step - previous_step,
            tokens_processed=self.tokens_processed - previous_tokens,
            tokens_since_last_sync=self.tokens_since_last_sync,
            loss=self.last_loss,
            loss_before=loss_before,
            loss_after=self.last_loss,
            final_loss=self.last_loss,
            grad_norm=grad_norm,
            num_parameters=int(self.parameters.size),
        )

    def get_named_state(self):
        return named_state_from_numpy(
            {"weights": self.parameters},
            global_version=self.global_version,
            device="cpu",
        )

    def get_state_fragments(self, fragment_ids: list[int] | None = None) -> list[TrainerFragment]:
        named_state = self.get_named_state()
        flat_state = flatten_named_state(named_state)
        layout = make_fragment_layout(total_elements=len(flat_state.values), num_fragments=1)
        flat_fragment = fragment_flat_state(flat_state, layout)[0]
        fragment = make_fragment(
            trainer_type=self.trainer_type,
            run_id=self.run_id,
            learner_id=self.learner_id,
            fragment_id=flat_fragment.fragment_id,
            global_version=self.global_version,
            data=np.asarray(flat_fragment.data, dtype=np.float64),
            tokens=self.tokens_since_last_sync,
            metadata={
                "trainer_state_kind": "named_tensors",
                "optimizer": "adamw",
                "optimizer_step": self.optimizer_step,
                "flat_state_checksum": flat_state.checksum,
                "named_state_checksum": named_state.checksum,
            },
            trainer_state_kind="named_tensors",
            flat_fragment=flat_fragment.model_dump(mode="json"),
            tensor_manifest=flat_state.manifest.model_dump(mode="json"),
        )
        validate_fragment(fragment)
        if fragment_ids is not None and 0 not in fragment_ids:
            return []
        return [fragment]

    def apply_global_update(
        self,
        fragments: list[TrainerFragment],
        *,
        global_version: int,
    ) -> None:
        if global_version < self.global_version:
            raise InvariantViolation("trainer global version cannot move backwards")
        if not fragments:
            return
        ordered = sorted(fragments, key=lambda fragment: fragment.fragment_id)
        self.parameters = np.concatenate(
            [np.asarray(fragment.data, dtype=np.float64).reshape(-1) for fragment in ordered]
        )
        self.global_version = global_version
        self.last_loss = self._loss()

    def get_full_state(self) -> TrainerState:
        named_state = self.get_named_state()
        flat_state = flatten_named_state(named_state)
        return make_state(
            trainer_type=self.trainer_type,
            run_id=self.run_id,
            learner_id=self.learner_id,
            global_version=self.global_version,
            local_step=self.local_step,
            tokens_processed=self.tokens_processed,
            tokens_since_last_sync=self.tokens_since_last_sync,
            parameters=np.asarray(flat_state.values, dtype=np.float64),
            metadata={
                "target_vector": self.target.astype(float).tolist(),
                "learning_rate": self.learning_rate,
                "throughput_tokens_per_step": self.throughput_tokens_per_step,
                "optimizer": "adamw",
                "optimizer_state": self._optimizer_state(),
                "real_training_mechanics_exercised": self.local_step > 0,
                "last_loss": self.last_loss,
            },
            trainer_state_kind="named_tensors",
            tensor_manifest=flat_state.manifest.model_dump(mode="json"),
            flat_state_checksum=flat_state.checksum,
            named_state_checksum=named_state.checksum,
        )

    def set_full_state(self, state: TrainerState, *, global_version: int) -> None:
        if global_version < 0:
            raise ValueError("global_version must be non-negative")
        self.run_id = state.run_id
        self.learner_id = state.learner_id
        self.global_version = global_version
        self.local_step = state.local_step
        self.tokens_processed = state.tokens_processed
        self.tokens_since_last_sync = state.tokens_since_last_sync
        self.parameters = np.asarray(state.parameters, dtype=np.float64)
        metadata = dict(state.metadata)
        if "target_vector" in metadata:
            self.target = np.asarray(metadata["target_vector"], dtype=np.float64)
        if "learning_rate" in metadata:
            self.learning_rate = float(metadata["learning_rate"])
        if "throughput_tokens_per_step" in metadata:
            self.throughput_tokens_per_step = int(metadata["throughput_tokens_per_step"])
        optimizer_state = dict(metadata.get("optimizer_state", {}))
        self.optimizer_step = int(optimizer_state.get("step", 0))
        self.exp_avg = np.asarray(
            optimizer_state.get("m", [0.0 for _ in self.parameters]),
            dtype=np.float64,
        )
        self.exp_avg_sq = np.asarray(
            optimizer_state.get("v", [0.0 for _ in self.parameters]),
            dtype=np.float64,
        )
        if self.exp_avg.shape != self.parameters.shape:
            self.exp_avg = np.zeros_like(self.parameters)
        if self.exp_avg_sq.shape != self.parameters.shape:
            self.exp_avg_sq = np.zeros_like(self.parameters)
        self.last_loss = float(metadata.get("last_loss", self._loss()))

    def checkpoint_payload(self) -> dict[str, Any]:
        return {"trainer_state": encode_state(self.get_full_state())}

    def restore_from_checkpoint(self, payload: dict[str, Any]) -> None:
        state = decode_state(str(payload["trainer_state"]))
        self.set_full_state(state, global_version=state.global_version)

    def estimate_state_bytes(self) -> int:
        return int(self.parameters.nbytes + self.exp_avg.nbytes + self.exp_avg_sq.nbytes)

    def health(self) -> TrainerHealth:
        state = self.get_full_state()
        return TrainerHealth(
            healthy=True,
            status="alive",
            local_step=self.local_step,
            tokens_processed=self.tokens_processed,
            tokens_since_last_sync=self.tokens_since_last_sync,
            global_version=self.global_version,
            state_checksum=state.checksum,
            state_bytes_estimate=self.estimate_state_bytes(),
            num_parameters=int(self.parameters.size),
            final_loss=self.last_loss,
            final_eval_loss=self.last_loss,
            nonfinite_detected=not bool(np.isfinite(self.parameters).all()),
        )

    def mark_update_accepted(self) -> None:
        self.tokens_since_last_sync = 0

    def _gradient(self) -> np.ndarray:
        return 2.0 * (self.parameters - self.target)

    def _loss(self) -> float:
        diff = self.parameters - self.target
        return float(np.dot(diff, diff))

    def _optimizer_state(self) -> dict[str, Any]:
        return {
            "step": self.optimizer_step,
            "m": self.exp_avg.astype(float).tolist(),
            "v": self.exp_avg_sq.astype(float).tolist(),
        }
