from __future__ import annotations

from lambda_m051_helpers import write_m051_inputs

from decodilo.lambda_cloud.m051_metadata_bootstrap_plan import (
    build_lambda_m051_metadata_bootstrap_plan_from_paths,
)


def test_m051_metadata_bootstrap_plan_uses_lifecycle_candidate_with_fresh_live_evidence(
    tmp_path,
):
    paths = write_m051_inputs(tmp_path)

    plan = build_lambda_m051_metadata_bootstrap_plan_from_paths(
        discovery_report=paths["discovery_m051"],
        bootstrap_authorization=paths["authorization"],
        ssh_key_selection=paths["ssh_key_selection"],
        price_snapshot=paths["price_snapshot"],
        lifecycle_success_record=paths["success"],
        lifecycle_closeout=paths["closeout"],
    )

    assert plan.plan_passed is True
    assert plan.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert plan.selected_region == "us-midwest-1"
    assert plan.metadata_only is True
    assert plan.ssh_used is False
    assert plan.remote_commands_allowed is False
    assert plan.package_install_allowed is False
    assert plan.training_allowed is False
    assert plan.launch_ready is False
    assert plan.launch_allowed is False


def test_m051_metadata_bootstrap_plan_blocks_without_fresh_live_candidate(tmp_path):
    paths = write_m051_inputs(tmp_path, include_candidate=False)

    plan = build_lambda_m051_metadata_bootstrap_plan_from_paths(
        discovery_report=paths["discovery_m051"],
        bootstrap_authorization=paths["authorization"],
        ssh_key_selection=paths["ssh_key_selection"],
        price_snapshot=paths["price_snapshot"],
        lifecycle_success_record=paths["success"],
        lifecycle_closeout=paths["closeout"],
    )

    assert plan.plan_passed is False
    assert "lifecycle_success_candidate_not_present_in_fresh_live_catalog" in plan.blockers
    assert plan.launch_ready is False
    assert plan.launch_allowed is False
