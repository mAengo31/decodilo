from decodilo.lambda_cloud.remote_bootstrap_scope import (
    build_lambda_remote_bootstrap_scope,
)


def test_remote_bootstrap_scope_defaults_to_metadata_only():
    report = build_lambda_remote_bootstrap_scope()

    assert report.bootstrap_scope_status == "scoped_for_future_m051_review"
    assert report.default_experiment_type == "lifecycle_plus_metadata_only"
    assert "training" in report.forbidden_actions
    assert "package_installation" in report.forbidden_actions
    assert "background_process" in report.forbidden_actions
    assert report.launch_ready is False
    assert report.launch_allowed is False
