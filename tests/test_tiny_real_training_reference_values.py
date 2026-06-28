from __future__ import annotations

from decodilo.dev.tiny_real_training_smoke import _compute_training_step


def test_tiny_real_training_reference_values_match_hand_computation():
    metrics = _compute_training_step()

    assert metrics["initial_loss"] == 9.0625
    assert metrics["gradients"] == {
        "weight": -7.5,
        "bias": -5.5,
    }
    assert abs(metrics["updated_parameters"]["weight"] - 0.5497499999333334) < 1e-12
    assert abs(metrics["updated_parameters"]["bias"] - -0.1998750000909091) < 1e-12
    assert metrics["optimizer_state"]["step"] == 1
    assert metrics["final_loss"] < metrics["initial_loss"]
