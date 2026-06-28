from __future__ import annotations

from lambda_m090_helpers import (
    make_m089r_workdir,
    write_m090_bounded_closeout_chain,
    write_scaffold_decision,
)

from decodilo.lambda_cloud.post_m089_next_step_decision import (
    build_lambda_post_m089_next_step_decision_from_paths,
)
from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    build_lambda_scaffold_completion_final_decision_from_paths,
    write_lambda_scaffold_completion_final_decision,
)
from decodilo.lambda_cloud.scientific_gap_assessment import (
    build_lambda_scientific_gap_assessment_from_path,
    write_lambda_scientific_gap_assessment,
)


def test_post_m089_next_step_decision_does_not_authorize_live_run(tmp_path):
    paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )
    scaffold = write_scaffold_decision(tmp_path)
    final_path = tmp_path / "scaffold-final.json"
    gap_path = tmp_path / "gaps.json"
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

    report = build_lambda_post_m089_next_step_decision_from_paths(
        scaffold_final_decision=final_path,
        scientific_gap_assessment=gap_path,
    )

    assert report.decision_status == "next_step_decided"
    assert report.recommended_path == "pause_and_analyze_bounded_experiment"
    assert report.no_automatic_live_authorization is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
