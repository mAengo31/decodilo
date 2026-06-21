from __future__ import annotations

import json

from lambda_m047_helpers import SUCCESS_SHAPE, live_instance_types_payload

from decodilo.lambda_cloud.live_region_selection import (
    build_lambda_live_region_selection,
    build_lambda_live_region_selection_from_paths,
)


def test_live_region_selection_prefers_prior_successful_region(tmp_path):
    raw = tmp_path / "instance-types.json"
    raw.write_text(json.dumps(live_instance_types_payload()), encoding="utf-8")

    report = build_lambda_live_region_selection_from_paths(
        instance_types=raw,
        candidate=SUCCESS_SHAPE,
        prior_successful_region="us-midwest-1",
    )

    assert report.selection_passed is True
    assert report.selected_region == "us-midwest-1"
    assert report.selection_source == "prior_successful_region"


def test_live_region_selection_rejects_stale_region():
    report = build_lambda_live_region_selection(
        live_regions=["us-midwest-1", "us-east-1"],
        candidate=SUCCESS_SHAPE,
        preferred_region="us-west-1",
    )

    assert report.selection_passed is False
    assert "preferred_region_not_live_available" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_live_region_selection_uses_deterministic_fallback():
    report = build_lambda_live_region_selection(
        live_regions=["us-midwest-1", "us-east-1"],
        candidate=SUCCESS_SHAPE,
    )

    assert report.selected_region == "us-east-1"
    assert report.selection_source == "deterministic_live_region"
