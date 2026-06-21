from decodilo.lambda_cloud.api_models import LambdaInstance
from decodilo.lambda_cloud.live_response_shapes import summarize_lambda_response_shape


def test_lambda_live_response_shape_summarizes_unknown_fixture_fields() -> None:
    instance = LambdaInstance.model_validate(
        {"instance_id": "i-shape", "status": "active", "tags": {}, "surprise": 1}
    )

    shape = summarize_lambda_response_shape([instance])

    assert shape.top_level_type == "list"
    assert shape.item_count == 1
    assert "surprise" in shape.unknown_fields_seen
    assert "instance_id" in shape.item_field_names


def test_lambda_live_response_shape_detects_pagination_marker() -> None:
    shape = summarize_lambda_response_shape({"items": [], "next_token": "n1"})

    assert shape.pagination_observed is True
    assert shape.item_count == 0
