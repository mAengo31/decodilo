from decodilo.sim.chaos import ChaosAction, ChaosEvent, ChaosPlan
from decodilo.sim.runner import SimulationConfig, run_simulation


def test_one_failed_learner_does_not_block_committed_sync_rounds() -> None:
    result = run_simulation(
        SimulationConfig(
            learners=4,
            vector_dim=4,
            num_fragments=2,
            steps=60,
            local_steps_per_sync=5,
            min_quorum=2,
            seed=7,
        ),
        chaos_plan=ChaosPlan(
            [
                ChaosEvent(tick=3, action=ChaosAction.FAIL_LEARNER, learner_id="learner-0"),
            ]
        ),
    )

    assert result.metrics.sync_rounds_committed > 0
    assert result.metrics.useful_tokens_accepted > 0
    assert result.metrics.learner_uptime["learner-0"].failed_ticks > 0

