"""Optional tiny CPU-capable PyTorch trainer adapter."""

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
)
from decodilo.trainer.synthetic_data import make_synthetic_regression_batch
from decodilo.trainer.torch_optional import require_torch


class TinyTorchMLPTrainer:
    """A tiny optional PyTorch trainer with a single CPU weight vector.

    The implementation deliberately avoids distributed PyTorch, CUDA, NCCL,
    torch.save, and pickle. It exists to exercise the adapter and named-state
    path before any real trainer is added.
    """

    trainer_type = "torch_tiny"

    def __init__(self) -> None:
        self.torch = None
        self.run_id = ""
        self.learner_id = ""
        self.global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0
        self.throughput_tokens_per_step = 0
        self.learning_rate = 0.0
        self.batch_size = 4
        self.seed = 0
        self.device = "cpu"
        self.weights = None
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
        torch = require_torch()
        self.torch = torch
        self.run_id = run_id
        self.learner_id = learner_id
        self.seed = seed
        self.learning_rate = config.learning_rate
        self.throughput_tokens_per_step = config.throughput_tokens_per_step
        self.batch_size = config.batch_size
        requested_device = config.device
        if requested_device.startswith("cuda") and not torch.cuda.is_available():
            raise InvariantViolation("cuda device requested but torch.cuda is unavailable")
        self.device = requested_device
        torch.manual_seed(seed)
        if initial_state is not None:
            self.set_full_state(initial_state, global_version=initial_state.global_version)
            return
        initial = (
            np.asarray(config.initial_vector, dtype=np.float32)
            if config.initial_vector is not None
            else np.zeros(config.vector_dim, dtype=np.float32)
        )
        self.weights = torch.tensor(initial, dtype=torch.float32, device=self.device)
        self.global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0

    def _torch(self):
        if self.torch is None:
            self.torch = require_torch()
        return self.torch

    def _weights_numpy(self) -> np.ndarray:
        assert self.weights is not None
        return self.weights.detach().cpu().numpy().astype(np.float32)

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        if num_steps < 0:
            raise ValueError("num_steps must be non-negative")
        torch = self._torch()
        assert self.weights is not None
        previous_step = self.local_step
        previous_tokens = self.tokens_processed
        for _ in range(num_steps):
            batch = make_synthetic_regression_batch(
                run_id=self.run_id,
                learner_id=self.learner_id,
                seed=self.seed,
                local_step=self.local_step,
                batch_size=self.batch_size,
                input_dim=int(self.weights.numel()),
                output_dim=int(self.weights.numel()),
                token_count=self.throughput_tokens_per_step,
            )
            inputs = torch.tensor(batch.inputs, dtype=torch.float32, device=self.device)
            targets = torch.tensor(batch.targets, dtype=torch.float32, device=self.device)
            self.weights.requires_grad_(True)
            prediction = inputs * self.weights
            loss = torch.mean((prediction - targets) ** 2)
            loss.backward()
            with torch.no_grad():
                assert self.weights.grad is not None
                self.weights -= self.learning_rate * self.weights.grad
                self.weights.grad = None
            self.weights.requires_grad_(False)
            self.local_step += 1
            self.tokens_processed += batch.token_count
            self.tokens_since_last_sync += batch.token_count
            self.last_loss = float(loss.detach().cpu().item())
        return TrainStepResult(
            local_steps=self.local_step - previous_step,
            tokens_processed=self.tokens_processed - previous_tokens,
            tokens_since_last_sync=self.tokens_since_last_sync,
            loss=self.last_loss,
        )

    def get_named_state(self):
        return named_state_from_numpy(
            {"weights": self._weights_numpy()},
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
        torch = self._torch()
        vector = np.concatenate(
            [np.asarray(fragment.data, dtype=np.float32).reshape(-1) for fragment in fragments]
        )
        self.weights = torch.tensor(vector, dtype=torch.float32, device=self.device)
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
                "learning_rate": self.learning_rate,
                "throughput_tokens_per_step": self.throughput_tokens_per_step,
                "batch_size": self.batch_size,
                "device": self.device,
                "seed": self.seed,
                "last_loss": self.last_loss,
            },
            trainer_state_kind="named_tensors",
            tensor_manifest=flat_state.manifest.model_dump(mode="json"),
            flat_state_checksum=flat_state.checksum,
            named_state_checksum=named_state.checksum,
        )

    def set_full_state(self, state: TrainerState, *, global_version: int) -> None:
        torch = self._torch()
        self.run_id = state.run_id
        self.learner_id = state.learner_id
        self.global_version = global_version
        self.local_step = state.local_step
        self.tokens_processed = state.tokens_processed
        self.tokens_since_last_sync = state.tokens_since_last_sync
        metadata = state.metadata
        self.learning_rate = float(metadata.get("learning_rate", self.learning_rate))
        self.throughput_tokens_per_step = int(
            metadata.get("throughput_tokens_per_step", self.throughput_tokens_per_step)
        )
        self.batch_size = int(metadata.get("batch_size", self.batch_size))
        self.device = str(metadata.get("device", self.device))
        self.seed = int(metadata.get("seed", self.seed))
        self.last_loss = metadata.get("last_loss")
        self.weights = torch.tensor(
            np.asarray(state.parameters, dtype=np.float32),
            dtype=torch.float32,
            device=self.device,
        )

    def checkpoint_payload(self) -> dict[str, Any]:
        return {"trainer_state": encode_state(self.get_full_state())}

    def restore_from_checkpoint(self, payload: dict[str, Any]) -> None:
        state = decode_state(str(payload["trainer_state"]))
        self.set_full_state(state, global_version=state.global_version)

    def estimate_state_bytes(self) -> int:
        return int(self._weights_numpy().nbytes)

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
            num_parameters=int(self._weights_numpy().size),
            final_loss=self.last_loss,
            nonfinite_detected=not bool(np.isfinite(self._weights_numpy()).all()),
        )

    def mark_update_accepted(self) -> None:
        self.tokens_since_last_sync = 0
