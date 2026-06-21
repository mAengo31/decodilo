from __future__ import annotations

import json

from lambda_m047_helpers import (
    SUCCESS_SHAPE,
    list_instance_types_payload,
    live_instance_types_payload,
)

from decodilo.lambda_cloud.live_instance_type_parser import (
    build_lambda_live_instance_type_parser_from_path,
)


def test_map_shaped_instance_types_parse_live_regions_and_price(tmp_path):
    raw = tmp_path / "instance-types-map.json"
    raw.write_text(json.dumps(live_instance_types_payload()), encoding="utf-8")

    report = build_lambda_live_instance_type_parser_from_path(raw)
    record = next(
        item for item in report.parsed_instance_types if item.instance_type_name == SUCCESS_SHAPE
    )

    assert report.response_shape == "map"
    assert report.parser_status == "parsed"
    assert record.available_regions == ["us-east-1", "us-midwest-1"]
    assert record.price_per_hour == 22.32
    assert record.live_available is True


def test_list_shaped_instance_types_parse(tmp_path):
    raw = tmp_path / "instance-types-list.json"
    raw.write_text(json.dumps(list_instance_types_payload()), encoding="utf-8")

    report = build_lambda_live_instance_type_parser_from_path(raw)

    assert report.response_shape == "list"
    assert report.parsed_instance_types[0].instance_type_name == SUCCESS_SHAPE
    assert report.parsed_instance_types[0].available_regions == ["us-midwest-1"]


def test_missing_regions_are_reported_clearly(tmp_path):
    raw = tmp_path / "instance-types-empty-region.json"
    payload = live_instance_types_payload()
    payload["data"][SUCCESS_SHAPE]["regions_with_capacity_available"] = []
    raw.write_text(json.dumps(payload), encoding="utf-8")

    report = build_lambda_live_instance_type_parser_from_path(raw)

    assert f"missing_live_regions:{SUCCESS_SHAPE}" in report.warnings
    assert report.launch_ready is False
    assert report.launch_allowed is False
