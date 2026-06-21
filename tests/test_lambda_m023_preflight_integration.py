from lambda_m023_helpers import (
    build_m023_evidence_package_from_refs,
    write_m023_core_artifacts,
)
from test_lambda_m020_report import _write_m020_inputs

from decodilo.lambda_cloud.first_launch_evidence_package import (
    write_lambda_first_launch_evidence_package,
)
from decodilo.lambda_cloud.m020_report import build_lambda_m020_report, write_lambda_m020_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight
from decodilo.lambda_cloud.real_mutation_review_record import (
    build_lambda_real_mutation_review_record,
    write_lambda_real_mutation_review_record,
)


def test_preflight_includes_m023_review_status_without_launch_enablement(tmp_path) -> None:
    m020_inputs = _write_m020_inputs(tmp_path, with_approval=True)
    m020 = build_lambda_m020_report(
        discovery_report=m020_inputs[0],
        read_only_audit=m020_inputs[1],
        ledger=m020_inputs[2],
        launch_plan=m020_inputs[3],
        teardown_plan=m020_inputs[4],
        price_snapshot=m020_inputs[5],
        credits=100,
        max_run_budget=50,
        planned_hours=0.5,
        safety_buffer_percentage=15,
        approval_manifest=m020_inputs[6],
    )
    m020_path = tmp_path / "m020-real.json"
    write_lambda_m020_report(m020_path, m020)
    refs = write_m023_core_artifacts(tmp_path / "m023")
    package = build_m023_evidence_package_from_refs(refs)
    package_path = tmp_path / "m023" / "evidence-package.json"
    write_lambda_first_launch_evidence_package(package_path, package)
    review = build_lambda_real_mutation_review_record(evidence_package=package)
    review_path = tmp_path / "m023" / "review.json"
    write_lambda_real_mutation_review_record(review_path, review)

    report = run_lambda_preflight(
        launch_plan=m020_inputs[3],
        teardown_plan=m020_inputs[4],
        live_discovery_report=m020_inputs[0],
        read_only_audit=m020_inputs[1],
        live_ledger=m020_inputs[2],
        m020_report=m020_path,
        m023_proposal=refs["proposal"],
        m023_safety_case=refs["safety"],
        m023_evidence_package=package_path,
        m023_review_record=review_path,
    )

    assert report.m023_review_summary is not None
    assert report.m023_review_summary["review_status"] == "design_review_ready"
    assert report.real_mutation_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert any("design review ready only" in warning for warning in report.warnings)
