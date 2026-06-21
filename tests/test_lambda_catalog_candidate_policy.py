from decodilo.lambda_cloud.catalog_candidate_policy import (
    default_lambda_catalog_candidate_policy,
)


def test_default_catalog_candidate_policy_excludes_recent_capacity_errors():
    report = default_lambda_catalog_candidate_policy()

    assert report.exclude_recent_capacity_error_shapes is True
    assert report.no_setup_cloud_init_training is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
