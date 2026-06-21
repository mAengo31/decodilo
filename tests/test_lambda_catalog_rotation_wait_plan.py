from lambda_m044_helpers import write_m044_inputs

from decodilo.lambda_cloud.catalog_rotation_wait_plan import (
    build_lambda_catalog_rotation_wait_plan_from_path,
)


def test_catalog_rotation_wait_plan_builds_for_declined_risk(tmp_path):
    paths = write_m044_inputs(tmp_path, accept=False, decline_wait=True)
    report = build_lambda_catalog_rotation_wait_plan_from_path(paths["operator"])

    assert report.plan_status == "wait_for_live_availability"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_rotation_wait_plan_not_applicable_for_acceptance(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = build_lambda_catalog_rotation_wait_plan_from_path(paths["operator"])

    assert report.plan_status == "not_applicable"
