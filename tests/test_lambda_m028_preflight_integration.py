from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_lambda_preflight_includes_m028_without_enabling_launch(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    report = run_lambda_preflight(
        launch_plan=paths["launch_plan"],
        teardown_plan=paths["lambda_teardown"],
        m028_report=paths["m028_report"],
        m029_authorization=paths["m029_authorization"],
    )

    assert report.m028_final_authorization_summary is not None
    assert report.launch_ready is False
    assert report.launch_allowed is False
