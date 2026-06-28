"""Normalized operation result for the pathway layer."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.operation.spec import OperationSafetyEnvelope


class OperationResult(BaseModel):
    """Backend-agnostic, normalized result of running an ``OperationSpec``.

    This is the single shape callers (and a future remote backend) consume,
    regardless of which backend produced it. It deliberately surfaces only the
    decoupled-DiLoCo evidence fields plus the safety envelope.
    """

    model_config = ConfigDict(frozen=True)

    result_schema_version: int = 1
    operation_name: str
    backend: str
    status: str = "completed"

    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    outer_momentum: float | None = None

    learners: int = 0
    final_global_version: int = 0
    sync_rounds_committed: int = 0
    trainer_final_loss: float | None = None

    training_attempted: bool = False
    real_training_mechanics_exercised: bool = False
    optimizer_state_present: bool = False
    nesterov_outer_optimizer_exercised: bool = False
    outer_optimizer_semantics_checked: bool = False
    pseudo_gradient_numeric_check_passed: bool | None = None
    pseudo_gradient_numeric_check_reason: str | None = None
    pseudo_gradient_numeric_rounds_checked: int = 0
    # Backward-compatible alias; local reports now set this from the numeric check.
    pseudo_gradient_check_passed: bool | None = None
    replay_passed: bool = False
    metric_validation_passed: bool = False
    syncer_recovered: bool = False

    # Remote/backend side-effect evidence. The OperationSafetyEnvelope remains
    # fail-closed for specs and dry-run paths; these fields report observed
    # effects from a real backend evidence package.
    remote_backend_enabled: bool = False
    billable_action_performed: bool = False
    remote_instance_count: int = 0
    network_path: str | None = None
    direct_tcp_probe_passed: bool | None = None
    firewall_rules_restored: bool | None = None
    final_instance_count: int | None = None
    restart_round: int | None = None
    rounds_after_restart: int = 0

    safety: OperationSafetyEnvelope = Field(default_factory=OperationSafetyEnvelope)
    backend_report: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
