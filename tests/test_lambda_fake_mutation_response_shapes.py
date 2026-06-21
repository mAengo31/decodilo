import json

import pytest

from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaLaunchResponse,
    FakeLambdaTerminateResponse,
)


def test_fake_launch_response_serializes() -> None:
    response = FakeLambdaLaunchResponse(instance_id="fake-i-abc", idempotency_key="k")
    payload = json.loads(response.to_json())

    assert payload["fake_only"] is True
    assert payload["real_lambda_api_used"] is False
    assert payload["billable_action_performed"] is False


def test_fake_terminate_response_serializes() -> None:
    response = FakeLambdaTerminateResponse(instance_id="fake-i-abc", idempotency_key="k")

    assert json.loads(response.to_json())["lifecycle_state"] == "terminated"


def test_fake_only_flag_required() -> None:
    with pytest.raises(ValueError, match="fake_only"):
        FakeLambdaLaunchResponse(
            instance_id="fake-i-abc",
            idempotency_key="k",
            fake_only=False,
        )


def test_real_looking_id_rejected() -> None:
    with pytest.raises(ValueError, match="fake mutation resource id"):
        FakeLambdaLaunchResponse(instance_id="i-real", idempotency_key="k")


def test_billable_action_false_required() -> None:
    with pytest.raises(ValueError, match="billable"):
        FakeLambdaLaunchResponse(
            instance_id="fake-i-abc",
            idempotency_key="k",
            billable_action_performed=True,
        )
