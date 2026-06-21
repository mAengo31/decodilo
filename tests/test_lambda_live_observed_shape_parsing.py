import json
from pathlib import Path

from decodilo.lambda_cloud.api_models import (
    LambdaImage,
    LambdaInstance,
    LambdaRegion,
    LambdaSSHKey,
)


def test_lambda_live_observed_name_based_shapes_parse_without_raw_key_material() -> None:
    payload = json.loads(
        Path("tests/fixtures/lambda_cloud/live_observed_shapes.json").read_text(
            encoding="utf-8"
        )
    )

    region = LambdaRegion.model_validate(payload["regions"][0])
    image = LambdaImage.model_validate(payload["images"][0])
    ssh_key = LambdaSSHKey.model_validate(payload["ssh_keys"][0])
    instance = LambdaInstance.model_validate(payload["instances"][0])

    assert region.region_id == "asia-northeast-1"
    assert region.metadata["description"] == "Osaka, Japan"
    assert image.image_id == "GPU Base 24.04"
    assert image.metadata["region"]["name"] == "us-west-1"
    assert ssh_key.key_id == "redacted-key-name"
    assert ssh_key.public_key_fingerprint
    assert ssh_key.metadata["public_key_redacted"] is True
    assert "public_key" not in ssh_key.metadata
    assert instance.instance_id == "redacted-instance-name"
    assert instance.instance_type_id == "gpu_1x_a10"
