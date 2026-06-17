import pytest

from decodilo.errors import InvariantViolation
from decodilo.trainer.torch_optimizer_state import (
    make_optimizer_policy,
    safe_optimizer_checkpoint_payload,
)


def test_torch_optimizer_policy_is_explicit() -> None:
    sgd = make_optimizer_policy("sgd")
    adamw = make_optimizer_policy("adamw")

    assert sgd.reset_on_global_update is True
    assert sgd.serialized_optimizer_state_supported is False
    assert adamw.optimizer_name == "adamw"
    assert adamw.serialized_optimizer_state_supported is False
    assert "not implemented" in adamw.notes


def test_optimizer_checkpoint_payload_fails_closed_if_tensor_state_claimed_supported() -> None:
    policy = make_optimizer_policy("sgd").model_copy(
        update={"serialized_optimizer_state_supported": True}
    )

    with pytest.raises(InvariantViolation, match="not implemented"):
        safe_optimizer_checkpoint_payload(policy)

