from lambda_m050_helpers import write_m050_inputs

from decodilo.lambda_cloud.m051_bootstrap_runbook_preview import (
    build_lambda_m051_bootstrap_runbook_preview_from_paths,
)


def test_m051_bootstrap_runbook_preview_is_non_executable(tmp_path):
    paths = write_m050_inputs(tmp_path)

    report = build_lambda_m051_bootstrap_runbook_preview_from_paths(
        authorization=paths["authorization"],
    )

    assert report.preview_status == "ready_for_future_m051_bootstrap_review"
    assert report.executable is False
    assert any("do not SSH" in step for step in report.runbook_steps)
    assert report.package_install_allowed is False
    assert report.training_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
