from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.m028_report import build_lambda_m028_report


def test_m028_report_builds_and_remains_non_launchable(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    report = build_lambda_m028_report(
        decision_record=paths["m028_decision"],
        m029_authorization=paths["m029_authorization"],
    )

    assert report.report_passed is True
    assert report.decision_record.status == "authorized_for_m029_one_instance_launch_attempt"
    assert report.launch_allowed is False

