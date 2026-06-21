from __future__ import annotations

from pathlib import Path

from lambda_m025_helpers import write_m025_core_artifacts

from decodilo.lambda_cloud.evidence_freshness import (
    evaluate_lambda_evidence_freshness,
    write_lambda_evidence_freshness_report,
)
from decodilo.lambda_cloud.human_review_manifest import (
    build_lambda_human_review_manifest,
    write_lambda_human_review_manifest,
)
from decodilo.lambda_cloud.human_review_validator import (
    validate_lambda_human_review,
    write_lambda_human_review_validation_report,
)
from decodilo.lambda_cloud.m026_report import build_lambda_m026_report, write_lambda_m026_report
from decodilo.lambda_cloud.m027_authorization_record import (
    build_lambda_m027_authorization_record,
    write_lambda_m027_authorization_record,
)
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    build_lambda_real_launch_blocker_matrix,
    write_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.real_launch_decision_gate import decide_lambda_real_launch
from decodilo.lambda_cloud.real_launch_decision_record import (
    write_lambda_real_launch_decision_record,
)


def write_m026_core_artifacts(tmp_path: Path) -> dict[str, Path]:
    paths = write_m025_core_artifacts(tmp_path)
    manifest = build_lambda_human_review_manifest(
        m025_evidence_package=paths["package"],
        go_no_go=paths["go"],
        acknowledge_all=True,
        requested_decision="approve_m027_minimal_real_mutation_implementation",
    )
    manifest_path = tmp_path / "human-review.json"
    write_lambda_human_review_manifest(manifest_path, manifest)

    validation = validate_lambda_human_review(manifest)
    validation_path = tmp_path / "human-review-validation.json"
    write_lambda_human_review_validation_report(validation_path, validation)

    freshness = evaluate_lambda_evidence_freshness(
        m019c_discovery=paths["discovery"],
        price_snapshot=paths["m020"],
        m025_review=paths["review"],
        semantic_audit=paths["semantic"],
    )
    freshness_path = tmp_path / "freshness.json"
    write_lambda_evidence_freshness_report(freshness_path, freshness)

    matrix = build_lambda_real_launch_blocker_matrix(
        human_review_validation=validation,
        freshness_report=freshness,
        semantic_audit=paths["semantic"],
    )
    matrix_path = tmp_path / "blocker-matrix.json"
    write_lambda_real_launch_blocker_matrix(matrix_path, matrix)

    decision_report = decide_lambda_real_launch(
        human_review_validation=validation,
        freshness_report=freshness,
        blocker_matrix=matrix,
        m025_review=paths["review"],
    )
    decision_path = tmp_path / "m026-decision.json"
    write_lambda_real_launch_decision_record(decision_path, decision_report.decision_record)

    authorization = build_lambda_m027_authorization_record(decision_path)
    authorization_path = tmp_path / "m027-authorization.json"
    write_lambda_m027_authorization_record(authorization_path, authorization)

    report = build_lambda_m026_report(
        decision_record=decision_report.decision_record,
        authorization_record=authorization,
        human_review_validation=validation,
        evidence_freshness=freshness,
        blocker_matrix=matrix,
    )
    report_path = tmp_path / "m026-report.json"
    write_lambda_m026_report(report_path, report)

    return {
        **paths,
        "human_review": manifest_path,
        "human_review_validation": validation_path,
        "freshness": freshness_path,
        "blocker_matrix": matrix_path,
        "decision": decision_path,
        "authorization": authorization_path,
        "m026_report": report_path,
    }
