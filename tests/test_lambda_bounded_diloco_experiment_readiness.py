from __future__ import annotations

from lambda_m088_helpers import (
    make_m087r_workdir,
    write_m088_parameter_fragment_closeout_chain,
    write_simple_closeout,
)

from decodilo.lambda_cloud.bounded_diloco_experiment_readiness import (
    build_lambda_bounded_diloco_experiment_readiness_from_path,
)
from decodilo.lambda_cloud.scaffold_complete_decision import (
    build_lambda_scaffold_complete_decision_from_paths,
    write_lambda_scaffold_complete_decision,
)


def test_bounded_diloco_experiment_readiness_passes_after_scaffold_decision(tmp_path):
    parameter_paths = write_m088_parameter_fragment_closeout_chain(
        tmp_path,
        make_m087r_workdir(tmp_path),
    )
    decision_path = tmp_path / "scaffold-decision.json"
    write_lambda_scaffold_complete_decision(
        decision_path,
        build_lambda_scaffold_complete_decision_from_paths(
            runtime_smoke_closeout=write_simple_closeout(tmp_path, "runtime"),
            learner_syncer_closeout=write_simple_closeout(tmp_path, "learner-syncer"),
            diloco_synthetic_closeout=write_simple_closeout(
                tmp_path, "diloco-synthetic"
            ),
            optimizer_closeout=write_simple_closeout(tmp_path, "optimizer"),
            integrated_closeout=write_simple_closeout(tmp_path, "integrated"),
            parameter_fragment_closeout=parameter_paths["closeout"],
        ),
    )

    report = build_lambda_bounded_diloco_experiment_readiness_from_path(
        scaffold_decision=decision_path,
    )

    assert (
        report.readiness_status
        == "ready_for_first_bounded_synthetic_diloco_experiment_planning"
    )
    assert report.learners == 1
    assert report.sync_rounds == 1
    assert report.fragments == 2
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.launch_ready is False
    assert report.launch_allowed is False
