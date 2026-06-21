from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_preflight_includes_m025_status_without_enabling_launch(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)

    report = run_lambda_preflight(
        m025_final_prelaunch_review=paths["review"],
        m025_go_no_go_record=paths["go"],
        m025_semantic_mutation_audit=paths["semantic"],
    )

    assert report.m025_final_prelaunch_summary is not None
    assert (
        report.m025_final_prelaunch_summary["go_no_go_status"]
        == "go_for_future_m026_real_launch_review"
    )
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert any("future launch review candidate only" in item for item in report.warnings)
