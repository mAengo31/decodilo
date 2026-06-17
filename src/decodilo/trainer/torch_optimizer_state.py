"""Explicit optimizer-state policy for optional torch trainers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from decodilo.errors import InvariantViolation


class OptimizerStatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    optimizer_name: str = "sgd"
    reset_on_global_update: bool = True
    serialized_optimizer_state_supported: bool = False
    notes: str = (
        "SGD without momentum stores scalar config only; optimizer resets on global update."
    )


def make_optimizer_policy(optimizer_name: str) -> OptimizerStatePolicy:
    normalized = optimizer_name.lower()
    if normalized == "sgd":
        return OptimizerStatePolicy(optimizer_name="sgd")
    if normalized == "adamw":
        return OptimizerStatePolicy(
            optimizer_name="adamw",
            reset_on_global_update=True,
            serialized_optimizer_state_supported=False,
            notes=(
                "AdamW state serialization is not implemented in this milestone; "
                "optimizer state is reset on global update/checkpoint restore."
            ),
        )
    raise InvariantViolation(f"unsupported torch optimizer {optimizer_name!r}")


def safe_optimizer_checkpoint_payload(policy: OptimizerStatePolicy) -> dict:
    if policy.serialized_optimizer_state_supported:
        raise InvariantViolation("serialized optimizer tensor state is not implemented")
    return {"optimizer_policy": policy.model_dump(mode="json")}
