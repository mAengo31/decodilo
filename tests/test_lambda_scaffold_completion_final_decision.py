from __future__ import annotations

from lambda_m090_helpers import (
    make_m089r_workdir,
    write_m090_bounded_closeout_chain,
    write_scaffold_decision,
)

from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    build_lambda_scaffold_completion_final_decision_from_paths,
)


def test_scaffold_completion_final_decision_completes_after_bounded_experiment(
    tmp_path,
):
    paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )
    scaffold = write_scaffold_decision(tmp_path)

    report = build_lambda_scaffold_completion_final_decision_from_paths(
        bounded_closeout=paths["closeout"],
        scaffold_decision=scaffold,
    )

    assert report.scaffold_final_status == "complete"
    assert report.bounded_experiment_completed is True
    assert report.no_more_scaffold_categories_by_default is True
    assert report.next_phase == "scientific_extension_or_real_training_planning"
    assert report.launch_ready is False
    assert report.launch_allowed is False
