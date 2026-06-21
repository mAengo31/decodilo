from decodilo.lambda_cloud.human_review_manifest import (
    LambdaHumanReviewManifest,
    build_lambda_human_review_manifest,
)
from decodilo.lambda_cloud.human_review_validator import validate_lambda_human_review


def test_incomplete_human_review_blocks():
    manifest = LambdaHumanReviewManifest(
        reviewed_evidence_package_hash="a" * 64,
        reviewed_go_no_go_hash="b" * 64,
    )

    report = validate_lambda_human_review(manifest)

    assert report.human_review_valid_for_m027_authorization is False
    assert report.blockers
    assert report.launch_allowed is False


def test_complete_human_review_validates_for_m027_only(tmp_path):
    package = tmp_path / "package.json"
    package.write_text("{}", encoding="utf-8")
    go = tmp_path / "go.json"
    go.write_text("{}", encoding="utf-8")
    manifest = build_lambda_human_review_manifest(
        m025_evidence_package=package,
        go_no_go=go,
        acknowledge_all=True,
        requested_decision="approve_m027_minimal_real_mutation_implementation",
    )

    report = validate_lambda_human_review(manifest)

    assert report.human_review_valid_for_m027_authorization is True
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
