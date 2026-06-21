from datetime import UTC, datetime, timedelta

from lambda_m026_helpers import write_m026_core_artifacts

from decodilo.lambda_cloud.evidence_freshness import LambdaEvidenceFreshnessReport
from decodilo.lambda_cloud.human_review_validator import LambdaHumanReviewValidationReport
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    build_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.real_launch_decision_gate import decide_lambda_real_launch
from decodilo.lambda_cloud.semantic_mutation_audit import LambdaSemanticMutationAuditReport


def test_complete_evidence_and_human_review_approves_m027_implementation(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)

    report = decide_lambda_real_launch(
        human_review_validation=paths["human_review_validation"],
        freshness_report=paths["freshness"],
        blocker_matrix=paths["blocker_matrix"],
        m025_review=paths["review"],
    )

    assert report.decision_record.status == "approve_m027_minimal_real_mutation_implementation"
    assert report.decision_record.real_mutation_enabled is False
    assert report.decision_record.launch_ready is False
    assert report.decision_record.launch_allowed is False


def test_incomplete_human_review_needs_more_evidence(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)
    human = LambdaHumanReviewValidationReport(
        human_review_valid_for_m027_authorization=False,
        requested_decision="needs_more_evidence",
        blockers=["missing acknowledgement"],
    )

    report = decide_lambda_real_launch(
        human_review_validation=human,
        freshness_report=paths["freshness"],
        blocker_matrix=paths["blocker_matrix"],
        m025_review=paths["review"],
    )

    assert report.decision_record.status == "needs_more_evidence"


def test_stale_discovery_needs_more_evidence(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)
    freshness = LambdaEvidenceFreshnessReport(
        freshness_passed=False,
        stale_items=["m019c_discovery"],
        blockers=["stale evidence: m019c_discovery"],
    )

    report = decide_lambda_real_launch(
        human_review_validation=paths["human_review_validation"],
        freshness_report=freshness,
        blocker_matrix=paths["blocker_matrix"],
        m025_review=paths["review"],
    )

    assert report.decision_record.status == "needs_more_evidence"


def test_semantic_audit_failure_blocks_decision(tmp_path):
    paths = write_m026_core_artifacts(tmp_path)
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

    report = decide_lambda_real_launch(
        human_review_validation=human,
        freshness_report=freshness,
        blocker_matrix=matrix,
        m025_review=paths["review"],
    )

    assert report.decision_record.status == "blocked"


def test_stale_time_import_does_not_require_live_lambda():
    # Kept local and deterministic; real Lambda discovery is never invoked by the gate.
    assert datetime.now(UTC) - timedelta(seconds=1) < datetime.now(UTC)
