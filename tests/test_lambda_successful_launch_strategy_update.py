from __future__ import annotations

from lambda_m047_helpers import SUCCESS_REGION, SUCCESS_SHAPE, write_m047_inputs

from decodilo.lambda_cloud.successful_launch_strategy_update import (
    build_lambda_successful_launch_strategy_update_from_paths,
)


def test_successful_launch_strategy_update_records_next_strategy(tmp_path):
    paths = write_m047_inputs(tmp_path)

    report = build_lambda_successful_launch_strategy_update_from_paths(
        success_record=paths["success"],
        live_region_selection=paths["region_selection"],
    )

    assert report.lifecycle_smoke_successful is True
    assert report.successful_candidate == SUCCESS_SHAPE
    assert report.successful_region == SUCCESS_REGION
    assert "use_live_instance_type_parser" in report.strategy_update
    assert "use_live_region_selection" in report.strategy_update
    assert report.next_recommended_stage == "test_profile_cleanup"
    assert report.launch_ready is False
    assert report.launch_allowed is False
