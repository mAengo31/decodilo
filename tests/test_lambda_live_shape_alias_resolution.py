from __future__ import annotations

import json

from lambda_m047_helpers import STALE_SHAPE, SUCCESS_SHAPE, live_instance_types_payload

from decodilo.lambda_cloud.live_shape_alias_resolution import (
    build_lambda_live_shape_alias_resolution_from_paths,
)


def test_stale_shape_alias_maps_to_canonical_live_id(tmp_path):
    raw = tmp_path / "instance-types.json"
    raw.write_text(json.dumps(live_instance_types_payload()), encoding="utf-8")

    report = build_lambda_live_shape_alias_resolution_from_paths(
        instance_types=raw,
        requested_shape=STALE_SHAPE,
    )

    assert report.alias_status == "alias_matched"
    assert report.canonical_live_id == SUCCESS_SHAPE
    assert report.launch_artifact_shape == SUCCESS_SHAPE
    assert report.blockers == []


def test_unknown_alias_blocks(tmp_path):
    raw = tmp_path / "instance-types.json"
    raw.write_text(json.dumps(live_instance_types_payload()), encoding="utf-8")

    report = build_lambda_live_shape_alias_resolution_from_paths(
        instance_types=raw,
        requested_shape="gpu_unknown",
    )

    assert report.alias_status in {"unknown_alias", "not_in_live_catalog"}
    assert report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
