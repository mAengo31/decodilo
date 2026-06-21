from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    load_lambda_final_prelaunch_evidence_package,
)
from decodilo.lambda_cloud.final_prelaunch_review import load_lambda_final_prelaunch_review
from decodilo.lambda_cloud.go_no_go_record import load_lambda_go_no_go_record
from decodilo.lambda_cloud.m025_report import build_lambda_m025_report


def test_m025_report_combines_artifacts_and_keeps_flags_false(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    report = build_lambda_m025_report(
        evidence_package=load_lambda_final_prelaunch_evidence_package(paths["package"]),
        final_prelaunch_review=load_lambda_final_prelaunch_review(paths["review"]),
        go_no_go_record=load_lambda_go_no_go_record(paths["go"]),
    )

    assert report.future_first_launch_candidate is True
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
