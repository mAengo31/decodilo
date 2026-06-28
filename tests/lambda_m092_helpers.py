from __future__ import annotations

from pathlib import Path

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
from decodilo.lambda_cloud.m091_report import (
    build_lambda_m091_report_from_paths,
    write_lambda_m091_report,
)
from decodilo.lambda_cloud.m092_report import (
    build_lambda_m092_report_from_paths,
    write_lambda_m092_report,
)
from decodilo.lambda_cloud.m093r_tiny_real_training_authorization import (
    build_lambda_m093r_tiny_real_training_authorization_from_paths,
    write_lambda_m093r_tiny_real_training_authorization,
)
from decodilo.lambda_cloud.m093r_tiny_real_training_runbook_preview import (
    build_lambda_m093r_tiny_real_training_runbook_preview_from_path,
    write_lambda_m093r_tiny_real_training_runbook_preview,
)
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
from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    discover_lambda_tiny_real_training_command,
    write_lambda_tiny_real_training_command_discovery,
)
from decodilo.lambda_cloud.tiny_real_training_policy import (
    build_lambda_tiny_real_training_policy_from_path,
    write_lambda_tiny_real_training_policy,
)
from decodilo.lambda_cloud.tiny_real_training_readiness import (
    build_lambda_tiny_real_training_readiness_from_path,
    write_lambda_tiny_real_training_readiness,
)


def write_m091_report(tmp_path: Path) -> Path:
    bounded_paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )
    scaffold_decision = write_scaffold_decision(tmp_path)
    scaffold_final_path = tmp_path / "scaffold-final.json"
    gap_path = tmp_path / "scientific-gap.json"
    post_m089_path = tmp_path / "post-m089.json"
    m090_path = tmp_path / "m090.json"
    summary_path = tmp_path / "result-summary.json"
    interpretation_path = tmp_path / "interpretation.json"
    boundaries_path = tmp_path / "boundaries.json"
    prioritization_path = tmp_path / "prioritization.json"
    next_branch_path = tmp_path / "next-branch.json"
    m091_path = tmp_path / "m091.json"
    write_lambda_scaffold_completion_final_decision(
        scaffold_final_path,
        build_lambda_scaffold_completion_final_decision_from_paths(
            bounded_closeout=bounded_paths["closeout"],
            scaffold_decision=scaffold_decision,
        ),
    )
    write_lambda_scientific_gap_assessment(
        gap_path,
        build_lambda_scientific_gap_assessment_from_path(
            bounded_artifact_audit=bounded_paths["audit"],
        ),
    )
    write_lambda_post_m089_next_step_decision(
        post_m089_path,
        build_lambda_post_m089_next_step_decision_from_paths(
            scaffold_final_decision=scaffold_final_path,
            scientific_gap_assessment=gap_path,
        ),
    )
    write_lambda_m090_report(
        m090_path,
        build_lambda_m090_report_from_paths(
            success_record=bounded_paths["success"],
            reconciliation=bounded_paths["reconciliation"],
            closeout=bounded_paths["closeout"],
            artifact_audit=bounded_paths["audit"],
            scaffold_final_decision=scaffold_final_path,
            scientific_gap_assessment=gap_path,
            next_step_decision=post_m089_path,
        ),
    )
    write_lambda_bounded_experiment_result_summary(
        summary_path,
        build_lambda_bounded_experiment_result_summary_from_paths(
            success_record=bounded_paths["success"],
            artifact_audit=bounded_paths["audit"],
            m090_report=m090_path,
        ),
    )
    write_lambda_bounded_experiment_evidence_interpretation(
        interpretation_path,
        build_lambda_bounded_experiment_evidence_interpretation_from_paths(
            result_summary=summary_path,
            closeout=bounded_paths["closeout"],
            scaffold_final_decision=scaffold_final_path,
        ),
    )
    write_lambda_scientific_claim_boundaries(
        boundaries_path,
        build_lambda_scientific_claim_boundaries_from_paths(
            evidence_interpretation=interpretation_path,
            artifact_audit=bounded_paths["audit"],
        ),
    )
    write_lambda_remaining_gap_prioritization(
        prioritization_path,
        build_lambda_remaining_gap_prioritization_from_paths(
            scientific_gap_assessment=gap_path,
            claim_boundaries=boundaries_path,
        ),
    )
    write_lambda_post_m090_next_branch_decision(
        next_branch_path,
        build_lambda_post_m090_next_branch_decision_from_paths(
            gap_prioritization=prioritization_path,
            evidence_interpretation=interpretation_path,
        ),
    )
    write_lambda_m091_report(
        m091_path,
        build_lambda_m091_report_from_paths(
            result_summary=summary_path,
            evidence_interpretation=interpretation_path,
            claim_boundaries=boundaries_path,
            gap_prioritization=prioritization_path,
            next_branch_decision=next_branch_path,
        ),
    )
    return m091_path


def write_m092_chain(tmp_path: Path) -> dict[str, Path]:
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    authorization_path = tmp_path / "authorization.json"
    preview_path = tmp_path / "preview.json"
    report_path = tmp_path / "m092.json"
    write_lambda_tiny_real_training_readiness(
        readiness_path,
        build_lambda_tiny_real_training_readiness_from_path(
            m091_report=write_m091_report(tmp_path),
        ),
    )
    write_lambda_tiny_real_training_command_discovery(
        discovery_path,
        discover_lambda_tiny_real_training_command(source_root=Path.cwd()),
    )
    write_lambda_tiny_real_training_policy(
        policy_path,
        build_lambda_tiny_real_training_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m093r_tiny_real_training_authorization(
        authorization_path,
        build_lambda_m093r_tiny_real_training_authorization_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m093r_tiny_real_training_runbook_preview(
        preview_path,
        build_lambda_m093r_tiny_real_training_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )
    write_lambda_m092_report(
        report_path,
        build_lambda_m092_report_from_paths(
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
            authorization=authorization_path,
            runbook_preview=preview_path,
        ),
    )
    return {
        "readiness": readiness_path,
        "discovery": discovery_path,
        "policy": policy_path,
        "authorization": authorization_path,
        "preview": preview_path,
        "report": report_path,
    }
