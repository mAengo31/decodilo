from __future__ import annotations

from lambda_m088_helpers import (
    make_m087r_workdir,
    write_m088_parameter_fragment_closeout_chain,
    write_simple_closeout,
)

from decodilo.lambda_cloud.scaffold_complete_decision import (
    build_lambda_scaffold_complete_decision_from_paths,
)


def test_scaffold_complete_decision_closes_scaffold_phase(tmp_path):
    parameter_paths = write_m088_parameter_fragment_closeout_chain(
        tmp_path,
        make_m087r_workdir(tmp_path),
    )

    report = build_lambda_scaffold_complete_decision_from_paths(
        runtime_smoke_closeout=write_simple_closeout(tmp_path, "runtime"),
        learner_syncer_closeout=write_simple_closeout(tmp_path, "learner-syncer"),
        diloco_synthetic_closeout=write_simple_closeout(tmp_path, "diloco-synthetic"),
        optimizer_closeout=write_simple_closeout(tmp_path, "optimizer"),
        integrated_closeout=write_simple_closeout(tmp_path, "integrated"),
        parameter_fragment_closeout=parameter_paths["closeout"],
    )

    assert report.scaffold_status == "scaffold_validation_complete"
    assert "remote parameter-fragment synthetic smoke" in report.completed_layers
    assert report.next_phase == "bounded_synthetic_diloco_experiment"
    assert report.no_more_independent_smoke_categories_by_default is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
