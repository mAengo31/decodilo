import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.human_review_manifest import (
    LambdaHumanReviewManifest,
    build_lambda_human_review_manifest,
)


def test_human_review_template_complete_for_m027_authorization(tmp_path):
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

    assert manifest.human_review_complete is True
    assert manifest.acknowledgements.missing() == []
    assert manifest.real_mutation_enabled is False
    assert manifest.launch_ready is False
    assert manifest.launch_allowed is False


def test_human_review_rejects_limits_above_policy():
    kwargs = {
        "reviewed_evidence_package_hash": "a" * 64,
        "reviewed_go_no_go_hash": "b" * 64,
    }

    with pytest.raises(ValidationError):
        LambdaHumanReviewManifest(**kwargs, max_budget=50.01)
    with pytest.raises(ValidationError):
        LambdaHumanReviewManifest(**kwargs, max_runtime_minutes=31)
    with pytest.raises(ValidationError):
        LambdaHumanReviewManifest(**kwargs, max_instances=2)


def test_human_review_rejects_requested_execution_status():
    with pytest.raises(ValidationError):
        LambdaHumanReviewManifest(
            reviewed_evidence_package_hash="a" * 64,
            reviewed_go_no_go_hash="b" * 64,
            requested_decision="execute_" + "now",
        )
