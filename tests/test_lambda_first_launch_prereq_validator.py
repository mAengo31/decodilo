from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    build_lambda_final_prelaunch_evidence_package,
)
from decodilo.lambda_cloud.first_launch_prereq_validator import (
    validate_lambda_first_launch_prereqs,
)


def test_prereq_validator_passes_complete_package(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    report = validate_lambda_first_launch_prereqs(paths["package"])

    assert report.prereq_passed_for_review is True
    assert report.launch_allowed is False


def test_prereq_validator_reports_missing_items(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    package = build_lambda_final_prelaunch_evidence_package(
        m019c_discovery=tmp_path / "missing.json",
        m019c_audit=paths["audit"],
        m020_report=paths["m020"],
        m022_readiness_package=paths["readiness"],
        m023_evidence_package=paths["m023_package"],
        m024_skeleton_audit=paths["skeleton"],
    )
    report = validate_lambda_first_launch_prereqs(package)

    assert report.prereq_passed_for_review is False
    assert "m019c_discovery" in report.missing_items
