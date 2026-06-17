"""Trainer evaluation helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    eval_loss: float
    eval_tokens: int = Field(ge=0)
    eval_steps: int = Field(ge=0)


def evaluate_if_supported(trainer, *, eval_steps: int = 2) -> EvalResult | None:
    evaluate = getattr(trainer, "evaluate", None)
    if evaluate is None:
        return None
    result = evaluate(eval_steps=eval_steps)
    if isinstance(result, EvalResult):
        return result
    return EvalResult.model_validate(result)
