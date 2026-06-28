from __future__ import annotations

from decodilo.dev.bounded_diloco_experiment import run_bounded_diloco_experiment
from decodilo.dev.diloco_optimizer_smoke import (
    EXPECTED_POST_INNER_PARAMETERS,
    EXPECTED_POST_OUTER_PARAMETERS,
    EXPECTED_PSEUDO_GRADIENT,
    INITIAL_PARAMETERS,
)


def test_bounded_diloco_experiment_reference_values_are_connected(tmp_path):
    report = run_bounded_diloco_experiment(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        fragments=2,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=tmp_path / "bounded-diloco-experiment.json",
    )

    assert report.full_vector_before == INITIAL_PARAMETERS
    assert report.post_inner_parameters == EXPECTED_POST_INNER_PARAMETERS
    assert report.full_vector_after == EXPECTED_POST_INNER_PARAMETERS
    assert report.reconstructed_vector_after == EXPECTED_POST_INNER_PARAMETERS
    assert report.protocol_committed_parameters == EXPECTED_POST_INNER_PARAMETERS
    assert report.pseudo_gradient == EXPECTED_PSEUDO_GRADIENT
    assert report.post_outer_parameters == EXPECTED_POST_OUTER_PARAMETERS
    assert report.expected_post_outer_parameters == EXPECTED_POST_OUTER_PARAMETERS
    assert report.fragment_ranges == [[0, 1], [2, 2]]
    assert report.fragment_shapes == [[2], [1]]
    assert report.fragment_versions_before == {"fragment_0": 0, "fragment_1": 0}
    assert report.fragment_versions_after == {"fragment_0": 1, "fragment_1": 1}
    assert report.fragment_schedule == [
        {
            "step": 1,
            "fragment_id": "fragment_0",
            "range": [0, 1],
            "update": [
                EXPECTED_POST_INNER_PARAMETERS[0] - INITIAL_PARAMETERS[0],
                EXPECTED_POST_INNER_PARAMETERS[1] - INITIAL_PARAMETERS[1],
            ],
        },
        {
            "step": 1,
            "fragment_id": "fragment_1",
            "range": [2, 2],
            "update": [
                EXPECTED_POST_INNER_PARAMETERS[2] - INITIAL_PARAMETERS[2],
            ],
        },
    ]
    assert report.protocol_optimizer_link_check_passed is True
    assert report.optimizer_fragment_link_check_passed is True
    assert report.protocol_fragment_link_check_passed is True
    assert report.integrated_reference_check_passed is True
    assert report.max_abs_error == 0.0
