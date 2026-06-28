from __future__ import annotations

from lambda_m090_helpers import (
    make_m089r_workdir,
    write_m090_bounded_closeout_chain,
    write_scaffold_decision,
)

from decodilo.lambda_cloud.bounded_experiment_evidence_interpretation import (
    build_lambda_bounded_experiment_evidence_interpretation_from_paths,
    write_lambda_bounded_experiment_evidence_interpretation,
)
from decodilo.lambda_cloud.bounded_experiment_result_summary import (
    build_lambda_bounded_experiment_result_summary_from_paths,
    write_lambda_bounded_experiment_result_summary,
)
from decodilo.lambda_cloud.m090_report import (
    build_lambda_m090_report_from_paths,
    write_lambda_m090_report,
)
from decodilo.lambda_cloud.m091_report import build_lambda_m091_report_from_paths
from decodilo.lambda_cloud.post_m089_next_step_decision import (
    build_lambda_post_m089_next_step_decision_from_paths,
    write_lambda_post_m089_next_step_decision,
)
from decodilo.lambda_cloud.post_m090_next_branch_decision import (
    build_lambda_post_m090_next_branch_decision_from_paths,
    write_lambda_post_m090_next_branch_decision,
)
from decodilo.lambda_cloud.remaining_gap_prioritization import (
    build_lambda_remaining_gap_prioritization_from_paths,
    write_lambda_remaining_gap_prioritization,
)
from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    build_lambda_scaffold_completion_final_decision_from_paths,
    write_lambda_scaffold_completion_final_decision,
)
from decodilo.lambda_cloud.scientific_claim_boundaries import (
    build_lambda_scientific_claim_boundaries_from_paths,
    write_lambda_scientific_claim_boundaries,
)
from decodilo.lambda_cloud.scientific_gap_assessment import (
    build_lambda_scientific_gap_assessment_from_path,
    write_lambda_scientific_gap_assessment,
)


def test_m091_scientific_decision_package_is_offline_and_truthful(tmp_path):
    bounded_paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )
    scaffold_decision = write_scaffold_decision(tmp_path)
    scaffold_final_path = tmp_path / "scaffold-final.json"
    scientific_gap_path = tmp_path / "scientific-gap.json"
    post_m089_decision_path = tmp_path / "post-m089-decision.json"
    m090_report_path = tmp_path / "m090-report.json"
    result_summary_path = tmp_path / "result-summary.json"
    interpretation_path = tmp_path / "interpretation.json"
    boundaries_path = tmp_path / "claim-boundaries.json"
    prioritization_path = tmp_path / "gap-prioritization.json"
    next_branch_path = tmp_path / "next-branch.json"

    write_lambda_scaffold_completion_final_decision(
        scaffold_final_path,
        build_lambda_scaffold_completion_final_decision_from_paths(
            bounded_closeout=bounded_paths["closeout"],
            scaffold_decision=scaffold_decision,
        ),
    )
    write_lambda_scientific_gap_assessment(
        scientific_gap_path,
        build_lambda_scientific_gap_assessment_from_path(
            bounded_artifact_audit=bounded_paths["audit"],
        ),
    )
    write_lambda_post_m089_next_step_decision(
        post_m089_decision_path,
        build_lambda_post_m089_next_step_decision_from_paths(
            scaffold_final_decision=scaffold_final_path,
            scientific_gap_assessment=scientific_gap_path,
        ),
    )
    write_lambda_m090_report(
        m090_report_path,
        build_lambda_m090_report_from_paths(
            success_record=bounded_paths["success"],
            reconciliation=bounded_paths["reconciliation"],
            closeout=bounded_paths["closeout"],
            artifact_audit=bounded_paths["audit"],
            scaffold_final_decision=scaffold_final_path,
            scientific_gap_assessment=scientific_gap_path,
            next_step_decision=post_m089_decision_path,
        ),
    )

    summary = build_lambda_bounded_experiment_result_summary_from_paths(
        success_record=bounded_paths["success"],
        artifact_audit=bounded_paths["audit"],
        m090_report=m090_report_path,
    )
    write_lambda_bounded_experiment_result_summary(result_summary_path, summary)
    interpretation = build_lambda_bounded_experiment_evidence_interpretation_from_paths(
        result_summary=result_summary_path,
        closeout=bounded_paths["closeout"],
        scaffold_final_decision=scaffold_final_path,
    )
    write_lambda_bounded_experiment_evidence_interpretation(
        interpretation_path,
        interpretation,
    )
    boundaries = build_lambda_scientific_claim_boundaries_from_paths(
        evidence_interpretation=interpretation_path,
        artifact_audit=bounded_paths["audit"],
    )
    write_lambda_scientific_claim_boundaries(boundaries_path, boundaries)
    prioritization = build_lambda_remaining_gap_prioritization_from_paths(
        scientific_gap_assessment=scientific_gap_path,
        claim_boundaries=boundaries_path,
    )
    write_lambda_remaining_gap_prioritization(prioritization_path, prioritization)
    decision = build_lambda_post_m090_next_branch_decision_from_paths(
        gap_prioritization=prioritization_path,
        evidence_interpretation=interpretation_path,
    )
    write_lambda_post_m090_next_branch_decision(next_branch_path, decision)

    report = build_lambda_m091_report_from_paths(
        result_summary=result_summary_path,
        evidence_interpretation=interpretation_path,
        claim_boundaries=boundaries_path,
        gap_prioritization=prioritization_path,
        next_branch_decision=next_branch_path,
    )

    assert summary.summary_status == "bounded_synthetic_diloco_experiment_summarized"
    assert "real_model_training" in summary.m089r_does_not_prove
    assert interpretation.scaffold_phase_complete is True
    assert interpretation.another_scaffold_run_justified is False
    assert boundaries.boundary_status == "claim_boundaries_defined"
    assert "real_model_training_completed" in boundaries.unsafe_claims
    assert prioritization.recommended_branch == "plan_tiny_real_training_smoke"
    assert decision.no_live_authorization is True
    assert report.report_passed is True
    assert report.scaffold_completion_status == "complete"
    assert report.recommended_next_branch == "plan_tiny_real_training_smoke"
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
