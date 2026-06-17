import numpy as np

from decodilo.sim.runner import SimulationConfig, run_simulation
from decodilo.syncer.replay import replay_event_log


def test_replaying_event_log_reconstructs_final_vector_and_metrics(tmp_path) -> None:
    log_path = tmp_path / "events.jsonl"
    result = run_simulation(
        SimulationConfig(
            learners=4,
            vector_dim=6,
            num_fragments=2,
            steps=80,
            local_steps_per_sync=8,
            min_quorum=2,
            seed=42,
        ),
        event_log_path=log_path,
    )

    replayed = replay_event_log(log_path)

    assert replayed.final_global_vector is not None
    np.testing.assert_allclose(replayed.final_global_vector, result.final_global_vector)
    assert replayed.accepted_useful_tokens == result.metrics.useful_tokens_accepted
    assert replayed.rejected_update_count == result.metrics.rejected_updates
    assert replayed.sync_rounds_committed == result.metrics.sync_rounds_committed
    assert replayed.sync_round_composition

