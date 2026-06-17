"""Numpy implementation of the synthetic convex trainer."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from decodilo.errors import InvariantViolation
from decodilo.trainer.flattening import (
    flatten_named_state,
    fragment_flat_state,
    make_fragment_layout,
)
from decodilo.trainer.named_state import named_state_from_numpy, tensor_array
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


def make_initial_vector(dimension: int) -> NDArray[np.float64]:
    """Create the deterministic default initial vector for convex training."""
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    return np.zeros(dimension, dtype=np.float64)


def make_target_vector(dimension: int, *, seed: int) -> NDArray[np.float64]:
    """Create a deterministic target vector from the run seed."""
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    rng = np.random.default_rng(seed)
    return rng.normal(loc=0.0, scale=1.0, size=dimension).astype(np.float64)


def convex_loss(
    vector: NDArray[np.float64],
    target: NDArray[np.float64],
) -> float:
    """Return ``||vector - target||^2`` for the synthetic objective."""
    params = np.asarray(vector, dtype=np.float64)
    target_array = np.asarray(target, dtype=np.float64)
    if params.shape != target_array.shape:
        raise ValueError("vector and target shapes must match")
    diff = params - target_array
    return float(np.dot(diff, diff))


class NumpyConvexTrainer:
    """Deterministic CPU trainer for ``minimize ||W - W_target||^2``."""

    trainer_type = "numpy_convex"

    def __init__(self) -> None:
        self.run_id = ""
        self.learner_id = ""
        self.global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0
        self.throughput_tokens_per_step = 0
        self.learning_rate = 0.0
        self.parameters = np.zeros(1, dtype=np.float64)
        self.target = np.zeros(1, dtype=np.float64)
        self.slow_factor = 1.0
        self.step_interval_ticks = 1
        self._tick_count = 0
        self.script: str | None = None

    def initialize(
        self,
        *,
        run_id: str,
        learner_id: str,
        seed: int,
        initial_state: TrainerState | None,
        config: TrainerConfig,
    ) -> None:
        self.run_id = run_id
        self.learner_id = learner_id
        self.learning_rate = config.learning_rate
        self.throughput_tokens_per_step = config.throughput_tokens_per_step
        self.script = config.script
        self.target = (
            np.asarray(config.target_vector, dtype=np.float64)
            if config.target_vector is not None
            else make_target_vector(config.vector_dim, seed=seed + 1)
        )
        if initial_state is not None:
            self.set_full_state(initial_state, global_version=initial_state.global_version)
        else:
            self.parameters = (
                np.asarray(config.initial_vector, dtype=np.float64)
                if config.initial_vector is not None
                else np.zeros(config.vector_dim, dtype=np.float64)
            )
            self.global_version = 0
            self.local_step = 0
            self.tokens_processed = 0
            self.tokens_since_last_sync = 0

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        if num_steps < 0:
            raise ValueError("num_steps must be non-negative")
        previous_tokens = self.tokens_processed
        previous_step = self.local_step
        for _ in range(num_steps):
            self._tick_count += 1
            if (self._tick_count - 1) % self.step_interval_ticks != 0:
                continue
            gradient = 2.0 * (self.parameters - self.target)
            self.parameters = self.parameters - self.learning_rate * gradient
            self.local_step += 1
            self.tokens_processed += self.throughput_tokens_per_step
            self.tokens_since_last_sync += self.throughput_tokens_per_step
        if self.local_step < previous_step or self.tokens_processed < previous_tokens:
            raise InvariantViolation("trainer local step and tokens must be monotonic")
        return TrainStepResult(
            local_steps=self.local_step - previous_step,
            tokens_processed=self.tokens_processed - previous_tokens,
            tokens_since_last_sync=self.tokens_since_last_sync,
            loss=convex_loss(self.parameters, self.target),
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
                "slow_factor": self.slow_factor,
                "step_interval_ticks": self.step_interval_ticks,
                "script": self.script,
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
        if state.trainer_state_kind == "named_tensors" and state.tensor_manifest:
            # The current convex trainer owns a single named tensor, "weights".
            manifest = state.tensor_manifest
            if manifest.get("tensors", [{}])[0].get("name") == "weights":
                self.parameters = np.asarray(state.parameters, dtype=np.float64)
            else:
                named = named_state_from_numpy(
                    {"weights": np.asarray(state.parameters, dtype=np.float64)},
                    global_version=global_version,
                )
                self.parameters = tensor_array(named, "weights").reshape(-1)
        else:
            self.parameters = np.asarray(state.parameters, dtype=np.float64)
        metadata = state.metadata
        if "target_vector" in metadata:
            self.target = np.asarray(metadata["target_vector"], dtype=np.float64)
        if "learning_rate" in metadata:
            self.learning_rate = float(metadata["learning_rate"])
        if "throughput_tokens_per_step" in metadata:
            self.throughput_tokens_per_step = int(metadata["throughput_tokens_per_step"])
        self.slow_factor = float(metadata.get("slow_factor", self.slow_factor))
        self.step_interval_ticks = int(
            metadata.get("step_interval_ticks", self.step_interval_ticks)
        )
        self.script = metadata.get("script")

    def checkpoint_payload(self) -> dict[str, Any]:
        return {"trainer_state": encode_state(self.get_full_state())}

    def restore_from_checkpoint(self, payload: dict[str, Any]) -> None:
        state = decode_state(str(payload["trainer_state"]))
        self.set_full_state(state, global_version=state.global_version)

    def estimate_state_bytes(self) -> int:
        return int(self.parameters.nbytes)

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
            final_loss=convex_loss(self.parameters, self.target),
            nonfinite_detected=not bool(np.isfinite(self.parameters).all()),
        )

    def mark_update_accepted(self) -> None:
        self.tokens_since_last_sync = 0

    def slow(self, factor: float) -> None:
        if factor <= 0:
            raise ValueError("slow factor must be positive")
        self.slow_factor = factor
        baseline = max(self.throughput_tokens_per_step, 1)
        self.throughput_tokens_per_step = max(1, int(round(baseline * factor)))
        self.step_interval_ticks = max(1, int(round(1.0 / min(factor, 1.0))))

    def restore_speed(self, baseline_tokens_per_step: int) -> None:
        self.slow_factor = 1.0
        self.throughput_tokens_per_step = baseline_tokens_per_step
        self.step_interval_ticks = 1
