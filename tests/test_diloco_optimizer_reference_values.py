from __future__ import annotations

from decodilo.dev.diloco_optimizer_smoke import (
    EXPECTED_POST_INNER_PARAMETERS,
    EXPECTED_POST_OUTER_PARAMETERS,
    EXPECTED_PSEUDO_GRADIENT,
    _run_reference_optimizer_smoke,
)


def test_optimizer_reference_values_are_deterministic():
    metrics = _run_reference_optimizer_smoke()

    assert metrics["post_inner_parameters"] == EXPECTED_POST_INNER_PARAMETERS
    assert metrics["pseudo_gradient"] == EXPECTED_PSEUDO_GRADIENT
    assert metrics["post_outer_parameters"] == EXPECTED_POST_OUTER_PARAMETERS
    assert metrics["inner_adamw_check_passed"] is True
    assert metrics["pseudo_gradient_check_passed"] is True
    assert metrics["outer_nesterov_check_passed"] is True
    assert metrics["optimizer_state_roundtrip_check_passed"] is True
    assert metrics["reference_value_check_passed"] is True
    assert metrics["max_abs_error"] == 0.0
