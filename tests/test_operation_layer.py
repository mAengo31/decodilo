"""Phase 2: operation/pathway layer tests.

These verify the backend-agnostic operation layer: the spec/safety/result
models fail closed, and the default local backend actually delegates to the
real learner/syncer runtime and returns normalized decoupled-DiLoCo evidence.

Boundary: local-only, CPU-only, synthetic. No Lambda, no remote backend, no
network beyond localhost, no spend.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from decodilo.operation import (
    LocalOperationBackend,
    OperationResult,
    OperationSafetyEnvelope,
    OperationSpec,
    run_operation,
)
from decodilo.operation.backend import OperationBackend


@pytest.mark.unit
def test_operation_spec_defaults_describe_adamw_nesterov() -> None:
    spec = OperationSpec()
    assert spec.inner_optimizer == "adamw"
    assert spec.outer_optimizer == "nesterov"
    assert spec.trainer_type == "tiny_adamw"
    assert spec.safety.launch_allowed is False
    assert spec.safety.network_scope == "localhost_only"


@pytest.mark.unit
def test_safety_envelope_fails_closed() -> None:
    with pytest.raises(ValidationError):
        OperationSafetyEnvelope(launch_allowed=True)
    with pytest.raises(ValidationError):
        OperationSafetyEnvelope(billable_action_performed=True)
    with pytest.raises(ValidationError):
        OperationSafetyEnvelope(paper_scale_training_claimed=True)


@pytest.mark.unit
def test_operation_spec_rejects_unsupported_choices() -> None:
    with pytest.raises(ValidationError):
        OperationSpec(inner_optimizer="sgd")
    with pytest.raises(ValidationError):
        OperationSpec(outer_optimizer="adam")
    with pytest.raises(ValidationError):
        OperationSpec(learners=1, min_quorum=2)


@pytest.mark.unit
def test_local_backend_satisfies_backend_protocol() -> None:
    assert isinstance(LocalOperationBackend(), OperationBackend)


@pytest.mark.integration
@pytest.mark.runtime
def test_run_operation_local_backend_end_to_end(tmp_path) -> None:
    spec = OperationSpec(steps=30, syncer_checkpoint_interval_rounds=1)
    result = run_operation(spec, workdir=tmp_path)

    assert isinstance(result, OperationResult)
    assert result.backend == "local"
    assert result.status == "completed"
    assert result.learners == 2

    # Decoupled-DiLoCo semantics surfaced through the operation layer.
    assert result.inner_optimizer_semantics == "adamw"
    assert result.outer_optimizer_semantics == "nesterov"
    assert result.outer_momentum == 0.9

    # Real (tiny) mechanics + runtime correctness evidence.
    assert result.final_global_version >= 1
    assert result.sync_rounds_committed >= 1
    assert result.training_attempted is True
    assert result.real_training_mechanics_exercised is True
    assert result.optimizer_state_present is True
    assert result.nesterov_outer_optimizer_exercised is True
    assert result.outer_optimizer_semantics_checked is True
    assert result.pseudo_gradient_numeric_check_passed is True
    assert result.pseudo_gradient_numeric_check_reason is None
    assert result.pseudo_gradient_numeric_rounds_checked >= 1
    assert result.pseudo_gradient_check_passed is True
    assert result.replay_passed is True
    assert result.metric_validation_passed is True

    # Safety envelope preserved end-to-end.
    assert result.safety.launch_ready is False
    assert result.safety.launch_allowed is False
    assert result.safety.billable_action_performed is False
    assert result.safety.remote_backend_enabled is False
    assert result.safety.network_scope == "localhost_only"
