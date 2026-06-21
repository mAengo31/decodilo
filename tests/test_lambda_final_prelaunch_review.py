from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    build_lambda_final_prelaunch_evidence_package,
)
from decodilo.lambda_cloud.final_prelaunch_review import build_lambda_final_prelaunch_review


def test_complete_fake_evidence_recommends_future_m026_review(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    review = build_lambda_final_prelaunch_review(
        evidence_package=paths["package"],
        operator_checklist=paths["checklist"],
        semantic_audit=paths["semantic"],
    )

    assert review.go_no_go_recommendation == "go_for_future_m026_real_launch_review"
    assert review.future_first_launch_candidate is True
    assert review.launch_allowed is False


def test_missing_skeleton_audit_blocks(tmp_path):
    paths = write_m025_core_artifacts(tmp_path)
    package = build_lambda_final_prelaunch_evidence_package(
        m019c_discovery=paths["discovery"],
        m019c_audit=paths["audit"],
        m020_report=paths["m020"],
        m022_readiness_package=paths["readiness"],
        m023_evidence_package=paths["m023_package"],
        m024_skeleton_audit=tmp_path / "missing-skeleton.json",
    )
    review = build_lambda_final_prelaunch_review(
        evidence_package=package,
        operator_checklist=paths["checklist"],
        semantic_audit=paths["semantic"],
    )

    assert review.go_no_go_recommendation == "blocked"
    assert any("m024_skeleton_audit" in blocker for blocker in review.blockers)
