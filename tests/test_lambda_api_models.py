import json

from decodilo.lambda_cloud.api_models import (
    LambdaInstance,
    LambdaInstanceType,
    LambdaRegion,
)
from decodilo.lambda_cloud.fixtures import load_lambda_fixture_data


def test_lambda_fixture_models_parse_and_preserve_unknown_fields() -> None:
    fixtures = load_lambda_fixture_data("tests/fixtures/lambda_cloud")
    instance_type = LambdaInstanceType.model_validate(
        {**fixtures["instance_types"][0], "new_field": "preserved"}
    )
    region = LambdaRegion.model_validate(fixtures["regions"][0])
    instance = LambdaInstance.model_validate(fixtures["instances"][0])

    assert instance_type.instance_type_id == "gpu_8x_h100_sxm"
    assert instance_type.metadata["new_field"] == "preserved"
    assert region.region_id == "us-west-1"
    assert instance.status == "active"


def test_lambda_model_json_roundtrip_is_stable() -> None:
    fixtures = load_lambda_fixture_data("tests/fixtures/lambda_cloud")
    model = LambdaInstanceType.model_validate(fixtures["instance_types"][0])

    payload = model.stable_json()

    assert LambdaInstanceType.model_validate_json(payload) == model
    assert json.loads(payload)["instance_type_id"] == "gpu_8x_h100_sxm"
