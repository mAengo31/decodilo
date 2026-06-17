import numpy as np

from decodilo.learner.fake_learner import FakeLearner
from decodilo.learner.learner_state import LearnerState
from decodilo.pricing.models import PriceProfile
from decodilo.protocol.messages import LearnerStatus
from decodilo.sim.runner import SimulationConfig, run_simulation


def test_simulation_metrics_token_invariants_and_cost_ratios() -> None:
    price = PriceProfile(
        provider="lambda",
        instance_type="test",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        gpu_memory_gb=80,
        price_per_gpu_hour=2.0,
        price_per_instance_hour=16.0,
        source_url="fixture",
        source_timestamp="2026-06-16T00:00:00Z",
    )
    result = run_simulation(
        SimulationConfig(learners=4, vector_dim=4, steps=40, local_steps_per_sync=5),
        price_profile=price,
    )
    metrics = result.metrics

    assert metrics.useful_tokens_accepted <= metrics.total_tokens_processed
    assert metrics.wasted_tokens == metrics.total_tokens_processed - metrics.useful_tokens_accepted
    assert 0.0 <= metrics.goodput_ratio <= 1.0
    assert metrics.cost_per_total_token is not None
    assert metrics.cost_per_useful_token is not None
    assert metrics.cost_per_useful_token >= metrics.cost_per_total_token


def test_failed_and_paused_learners_do_not_process_tokens() -> None:
    learner = FakeLearner(
        LearnerState(
            learner_id="learner-0",
            local_step=0,
            tokens_processed=0,
            parameters=np.zeros(2),
            last_global_version_seen=0,
            status=LearnerStatus.ALIVE,
            throughput_tokens_per_step=100,
        )
    )
    target = np.ones(2)

    learner.tick(target_vector=target)
    tokens_after_alive = learner.state.tokens_processed
    learner.pause()
    learner.tick(target_vector=target)
    assert learner.state.tokens_processed == tokens_after_alive
    assert learner.state.local_step == 1

    learner.fail()
    learner.tick(target_vector=target)
    assert learner.state.tokens_processed == tokens_after_alive
    assert learner.state.local_step == 1

