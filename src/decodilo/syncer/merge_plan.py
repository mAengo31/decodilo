"""Typed merge plans for binary out-of-core merge."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MergePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    round_id: str
    fragment_id: int = Field(ge=0)
    input_artifact_refs: dict[str, dict[str, Any]]
    global_artifact_ref: dict[str, Any] | None = None
    output_artifact_target: dict[str, Any] | None = None
    token_weights: dict[str, float]
    outer_lr: float = 1.0
    dtype: str
    shape: list[int]
    total_elements: int = Field(gt=0)
    chunk_size_bytes: int = Field(gt=0)
    max_working_bytes: int = Field(gt=0)
    finite_check_policy: str = "require_finite"
    numeric_merge_performed: bool = True
    simulation_only: bool = False
    notes: list[str] = Field(default_factory=list)

    @field_validator("dtype")
    @classmethod
    def _dtype_supported(cls, value: str) -> str:
        if value not in {"float16", "float32", "float64"}:
            raise ValueError("out-of-core merge supports float16, float32, and float64")
        return value

    @field_validator("finite_check_policy")
    @classmethod
    def _finite_policy_supported(cls, value: str) -> str:
        if value not in {"require_finite", "allow_nonfinite"}:
            raise ValueError("unknown finite_check_policy")
        return value

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def normalized_token_weights(token_counts: dict[str, int]) -> dict[str, float]:
    total = sum(max(tokens, 0) for tokens in token_counts.values())
    return {
        learner_id: (max(tokens, 0) / total if total else 0.0)
        for learner_id, tokens in token_counts.items()
    }
