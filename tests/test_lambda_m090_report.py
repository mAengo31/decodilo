from __future__ import annotations

from lambda_m090_helpers import (
    make_m089r_workdir,
    write_m090_bounded_closeout_chain,
    write_scaffold_decision,
)

from decodilo.lambda_cloud.m090_report import build_lambda_m090_report_from_paths
from decodilo.lambda_cloud.post_m089_next_step_decision import (
    build_lambda_post_m089_next_step_decision_from_paths,
    write_lambda_post_m089_next_step_decision,
)
from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    build_lambda_scaffold_completion_final_decision_from_paths,
    write_lambda_scaffold_completion_final_decision,
)
from decodilo.lambda_cloud.scientific_gap_assessment import (
    build_lambda_scientific_gap_assessment_from_path,
    write_lambda_scientific_gap_assessment,
)


def test_m090_report_passes_and_creates_no_authorization(tmp_path):
    paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )
    scaffold = write_scaffold_decision(tmp_path)
    final_path = tmp_path / "scaffold-final.json"
    gap_path = tmp_path / "gaps.json"
    decision_path = tmp_path / "next-step.json"
    write_lambda_scaffold_completion_final_decision(
        final_path,
        build_lambda_scaffold_completion_final_decision_from_paths(
            bounded_closeout=paths["closeout"],
            scaffold_decision=scaffold,
        ),
    )
    write_lambda_scientific_gap_assessment(
        gap_path,
        build_lambda_scientific_gap_assessment_from_path(
            bounded_artifact_audit=paths["audit"],
        ),
    )
    write_lambda_post_m089_next_step_decision(
        decision_path,
        build_lambda_post_m089_next_step_decision_from_paths(
            scaffold_final_decision=final_path,
            scientific_gap_assessment=gap_path,
        ),
    )

    report = build_lambda_m090_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        artifact_audit=paths["audit"],
        scaffold_final_decision=final_path,
        scientific_gap_assessment=gap_path,
        next_step_decision=decision_path,
    )

    assert report.report_passed is True
    assert report.bounded_closeout_succeeded is True
    assert report.bounded_artifact_audit_passed is True
    assert report.scaffold_final_status == "complete"
    assert report.recommended_next_path == "pause_and_analyze_bounded_experiment"
    assert report.no_new_live_authorization is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
