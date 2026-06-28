from __future__ import annotations

from decodilo.dev.parameter_fragment_smoke import (
    EXPECTED_VECTOR_AFTER,
    FRAGMENT_RANGES,
    INITIAL_VECTOR,
    run_parameter_fragment_smoke,
)


def test_parameter_fragment_smoke_reference_values_are_deterministic(tmp_path):
    report = run_parameter_fragment_smoke(
        synthetic=True,
        fragments=2,
        max_steps=1,
        out=tmp_path / "parameter-fragment-smoke.json",
    )

    assert report.full_vector_before == INITIAL_VECTOR
    assert report.fragment_ranges == FRAGMENT_RANGES
    assert report.fragment_schedule == [
        {
            "step": 1,
            "fragment_id": "fragment_1",
            "range": [2, 3],
            "update": [0.25, -0.5],
        }
    ]
    assert report.full_vector_after == EXPECTED_VECTOR_AFTER
    assert report.reconstructed_vector_after == EXPECTED_VECTOR_AFTER
    assert report.expected_vector_after == EXPECTED_VECTOR_AFTER
    assert report.fragment_versions_after == {"fragment_0": 0, "fragment_1": 1}
    assert report.fragment_schedule_check_passed is True
    assert report.fragment_state_roundtrip_check_passed is True
    assert report.per_fragment_reference_check_passed is True
    assert report.global_reference_check_passed is True
    assert report.max_abs_error == 0.0
