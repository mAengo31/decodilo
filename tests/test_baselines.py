from decodilo.sim.baselines import run_decoupled_baseline, run_synchronous_baseline
from decodilo.sim.chaos import ChaosAction, ChaosEvent, ChaosPlan
from decodilo.sim.runner import SimulationConfig


def test_synchronous_and_decoupled_both_progress_without_failures() -> None:
    config = SimulationConfig(
        learners=4,
        vector_dim=4,
        steps=40,
        local_steps_per_sync=5,
        min_quorum=4,
        seed=5,
    )

    synchronous = run_synchronous_baseline(config)
    decoupled = run_decoupled_baseline(config)

    assert synchronous.metrics.committed_sync_rounds > 0
    assert decoupled.metrics.committed_sync_rounds > 0


def test_decoupled_commits_more_than_synchronous_with_one_failed_learner() -> None:
    config = SimulationConfig(
        learners=4,
        vector_dim=4,
        steps=50,
        local_steps_per_sync=5,
        min_quorum=2,
        seed=9,
    )
    chaos = ChaosPlan(
        [ChaosEvent(tick=3, action=ChaosAction.FAIL_LEARNER, learner_id="learner-0")]
    )

    synchronous = run_synchronous_baseline(config, chaos_plan=chaos)
    decoupled = run_decoupled_baseline(config, chaos_plan=chaos)

    assert decoupled.metrics.committed_sync_rounds > synchronous.metrics.committed_sync_rounds


def test_all_healthy_identical_sync_is_not_magically_better_decoupled() -> None:
    config = SimulationConfig(
        learners=4,
        vector_dim=4,
        steps=40,
        local_steps_per_sync=5,
        min_quorum=4,
        seed=13,
    )

    synchronous = run_synchronous_baseline(config)
    decoupled = run_decoupled_baseline(config)

    assert abs(synchronous.final_loss - decoupled.final_loss) < 1e-12

