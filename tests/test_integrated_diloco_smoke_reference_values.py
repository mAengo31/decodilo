from __future__ import annotations

from decodilo.dev.diloco_optimizer_smoke import (
    EXPECTED_POST_INNER_PARAMETERS,
    EXPECTED_POST_OUTER_PARAMETERS,
    EXPECTED_PSEUDO_GRADIENT,
)
from decodilo.dev.integrated_diloco_smoke import run_integrated_diloco_smoke


def test_integrated_diloco_smoke_reference_values_match_optimizer_smoke(tmp_path):
    report = run_integrated_diloco_smoke(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=tmp_path / "integrated.json",
    )

    assert report.post_inner_parameters == EXPECTED_POST_INNER_PARAMETERS
    assert report.pseudo_gradient == EXPECTED_PSEUDO_GRADIENT
    assert report.post_outer_parameters == EXPECTED_POST_OUTER_PARAMETERS
    assert report.expected_post_outer_parameters == EXPECTED_POST_OUTER_PARAMETERS
    assert report.protocol_committed_parameters == EXPECTED_POST_INNER_PARAMETERS
    assert report.protocol_optimizer_link_check_passed is True
    assert report.max_abs_error == 0.0
