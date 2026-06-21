import json

import pytest

from decodilo.lambda_cloud.fake_lifecycle_state import (
    FakeLambdaLifecycleState,
    FakeLambdaResourceRecord,
    make_fake_resource_id,
    validate_fake_lifecycle_invariants,
)


def test_fake_lifecycle_state_launch_and_teardown_transitions() -> None:
    state = FakeLambdaLifecycleState(lifecycle_id="life")
    resource_id = make_fake_resource_id("instance", lifecycle_id="life", index=0)
    state = state.add_resource(
        FakeLambdaResourceRecord(
            resource_id=resource_id,
            resource_type="instance",
            state="planned",
        )
    )

    for target in ["launch_requested", "launching", "running", "healthy"]:
        state, transition = state.transition(resource_id, target)
        assert transition.to_state == target
    for target in ["terminate_requested", "terminating", "terminated"]:
        state, transition = state.transition(resource_id, target)
        assert transition.to_state == target

    report = validate_fake_lifecycle_invariants(state)
    assert report.passed is True
    assert report.real_lambda_api_used is False


def test_fake_lifecycle_state_rejects_invalid_transition() -> None:
    resource_id = make_fake_resource_id("instance", lifecycle_id="life", index=0)
    state = FakeLambdaLifecycleState(lifecycle_id="life").add_resource(
        FakeLambdaResourceRecord(
            resource_id=resource_id,
            resource_type="instance",
            state="planned",
        )
    )

    with pytest.raises(ValueError, match="invalid fake transition"):
        state.transition(resource_id, "terminated")


def test_fake_lifecycle_state_rejects_real_looking_id() -> None:
    with pytest.raises(ValueError, match="must start"):
        FakeLambdaResourceRecord(
            resource_id="i-real-looking",
            resource_type="instance",
            state="planned",
        )


def test_fake_lifecycle_state_json_roundtrip() -> None:
    resource_id = make_fake_resource_id("instance", lifecycle_id="life", index=1)
    state = FakeLambdaLifecycleState(lifecycle_id="life").add_resource(
        FakeLambdaResourceRecord(
            resource_id=resource_id,
            resource_type="instance",
            state="planned",
        )
    )

    payload = json.loads(state.to_json())
    restored = FakeLambdaLifecycleState.model_validate(payload)

    assert restored.resources[resource_id].resource_id == resource_id
    assert restored.fake_only is True
