"""Scripted trainer adapter for deterministic fault tests."""

from __future__ import annotations

import numpy as np

from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.state import TrainerFragment, TrainStepResult
from decodilo.trainer.state_codec import make_fragment


class ScriptedTrainer(NumpyConvexTrainer):
    """Numpy trainer with deterministic scripted update behavior for tests."""

    trainer_type = "scripted"

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        result = super().train_local_steps(num_steps)
        script = self.script or "normal"
        if script == "divergent":
            self.parameters = self.parameters + 1000.0
        return result

    def get_state_fragments(self, fragment_ids: list[int] | None = None) -> list[TrainerFragment]:
        script = self.script or "normal"
        base = super().get_state_fragments(fragment_ids=fragment_ids)
        if not base:
            return []
        base_fragment = base[0]
        tokens = base_fragment.tokens
        data = np.asarray(base_fragment.data, dtype=np.float64)
        global_version = base_fragment.global_version
        if script == "zero_tokens":
            tokens = 0
        elif script == "stale":
            global_version = max(global_version - 10, 0)
        elif script == "divergent":
            data = data + 1000.0
        fragment = make_fragment(
            trainer_type=self.trainer_type,
            run_id=self.run_id,
            learner_id=self.learner_id,
            fragment_id=0,
            global_version=global_version,
            data=np.asarray(data, dtype=np.float64),
            tokens=tokens,
            metadata={**base_fragment.metadata, "script": script},
            trainer_state_kind=base_fragment.trainer_state_kind,
            flat_fragment=base_fragment.flat_fragment,
            tensor_manifest=base_fragment.tensor_manifest,
        )
        if script == "malformed_checksum":
            fragment = fragment.model_copy(update={"checksum": "bad"})
        return [fragment]
