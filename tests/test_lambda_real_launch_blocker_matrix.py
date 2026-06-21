from decodilo.lambda_cloud.evidence_freshness import LambdaEvidenceFreshnessReport
from decodilo.lambda_cloud.human_review_validator import LambdaHumanReviewValidationReport
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    build_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.semantic_mutation_audit import LambdaSemanticMutationAuditReport


def test_missing_human_review_blocks_m027_authorization():
    matrix = build_lambda_real_launch_blocker_matrix()

    assert matrix.m027_authorization_blocked is True
    assert any(blocker.category == "missing_human_review" for blocker in matrix.blockers)


def test_complete_evidence_clears_m027_blockers_but_not_launch_blockers():
    human = LambdaHumanReviewValidationReport(
        human_review_valid_for_m027_authorization=True,
        requested_decision="approve_m027_minimal_real_mutation_implementation",
    )
    freshness = LambdaEvidenceFreshnessReport(freshness_passed=True)
    semantic = LambdaSemanticMutationAuditReport(passed=True, scanned_files=1)

    matrix = build_lambda_real_launch_blocker_matrix(
        human_review_validation=human,
        freshness_report=freshness,
        semantic_audit=semantic,
    )

    assert matrix.m027_authorization_blocked is False
    assert matrix.real_launch_execution_blocked is True
    assert any(blocker.category == "launch_disabled_by_policy" for blocker in matrix.blockers)


def test_semantic_audit_failure_blocks_m027():
    human = LambdaHumanReviewValidationReport(
        human_review_valid_for_m027_authorization=True,
        requested_decision="approve_m027_minimal_real_mutation_implementation",
    )
    freshness = LambdaEvidenceFreshnessReport(freshness_passed=True)
    semantic = LambdaSemanticMutationAuditReport(
        passed=False,
        scanned_files=1,
        blockers=["synthetic blocker"],
    )

    matrix = build_lambda_real_launch_blocker_matrix(
        human_review_validation=human,
        freshness_report=freshness,
        semantic_audit=semantic,
    )

    assert matrix.m027_authorization_blocked is True
    assert any(
        blocker.category == "semantic_mutation_audit_failed" for blocker in matrix.blockers
    )
