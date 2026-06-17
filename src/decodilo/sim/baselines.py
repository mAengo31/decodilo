"""Simple CPU baselines for comparing decoupled quorum behavior."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from decodilo.learner.fake_learner import FakeLearner
from decodilo.learner.learner_state import LearnerState
from decodilo.protocol.messages import LearnerStatus
from decodilo.sim.chaos import ChaosPlan
from decodilo.sim.fake_model import convex_loss, make_initial_vector, make_target_vector
from decodilo.sim.metrics import LearnerUptime, SimulationMetrics
from decodilo.sim.runner import SimulationConfig, SimulationResult, run_simulation
from decodilo.syncer.event_log import EventLog
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge


@dataclass(frozen=True)
class BaselineResult:
    final_global_vector: NDArray[np.float64]
    final_global_version: int
    final_loss: float
    metrics: SimulationMetrics


def _make_learners(
    config: SimulationConfig,
    initial_vector: NDArray[np.float64],
) -> dict[str, FakeLearner]:
    learners: dict[str, FakeLearner] = {}
    for index in range(config.learners):
        learner_id = f"learner-{index}"
        throughput = 100 + index * 10
        learners[learner_id] = FakeLearner(
            LearnerState(
                learner_id=learner_id,
                local_step=0,
                tokens_processed=0,
                parameters=initial_vector.copy(),
                last_global_version_seen=0,
                status=LearnerStatus.ALIVE,
                throughput_tokens_per_step=throughput,
            ),
            learning_rate=config.learner_lr,
        )
    return learners


def run_synchronous_baseline(
    config: SimulationConfig,
    *,
    chaos_plan: ChaosPlan | None = None,
) -> BaselineResult:
    """Run a blocking all-learner sync baseline.

    Every learner must be alive and ready at the same sync boundary. If any
    learner is failed or paused, the round is skipped instead of using quorum.
    """

    initial_global = make_initial_vector(config.vector_dim)
    target = make_target_vector(config.vector_dim, seed=config.seed + 1)
    learners = _make_learners(config, initial_global)
    chaos = chaos_plan or ChaosPlan()
    event_log = EventLog(run_id="sync-baseline")
    global_vector = initial_global.copy()
    global_version = 0
    committed = 0
    skipped = 0
    useful_tokens = 0

    for tick in range(config.steps):
        chaos.apply(
            tick=tick,
            learners=learners,
            event_log=event_log,
            current_global_version=global_version,
        )
        for learner_id in sorted(learners):
            learners[learner_id].tick(target_vector=target)

        ready = all(
            learner.state.local_step > 0
            and learner.state.local_step % config.local_steps_per_sync == 0
            and learner.state.tokens_since_last_sync > 0
            for learner in learners.values()
        )
        all_alive = all(
            learner.state.status == LearnerStatus.ALIVE for learner in learners.values()
        )
        if not ready:
            continue
        if not all_alive:
            skipped += 1
            continue

        updates = [learner.make_update() for learner in learners.values()]
        merge = token_weighted_merge(
            global_vector,
            [
                LearnerDelta(
                    learner_id=update.learner_id,
                    vector=update.vector,
                    tokens=update.tokens,
                    global_version_seen=update.global_version_seen,
                )
                for update in updates
            ],
            optimizer=SGDOuterOptimizer(outer_lr=config.outer_lr),
        )
        global_vector = merge.new_global_vector.copy()
        global_version += 1
        committed += 1
        useful_tokens += merge.useful_tokens
        for learner in learners.values():
            learner.mark_update_accepted()
            learner.receive_global(global_vector, global_version=global_version)

    total_tokens = sum(learner.state.tokens_processed for learner in learners.values())
    learner_uptime = {
        learner_id: LearnerUptime(
            learner_id=learner_id,
            alive_ticks=learner.state.uptime_ticks,
            paused_ticks=learner.state.paused_ticks,
            failed_ticks=learner.state.failed_ticks,
        )
        for learner_id, learner in learners.items()
    }
    final_loss = convex_loss(global_vector, target)
    metrics = SimulationMetrics(
        total_tokens_processed=total_tokens,
        useful_tokens_accepted=useful_tokens,
        rejected_tokens=0,
        stale_tokens=0,
        wasted_tokens=total_tokens - useful_tokens,
        committed_sync_rounds=committed,
        skipped_sync_rounds=skipped,
        rejected_fragments=0,
        stale_fragments=0,
        learner_uptime_ticks={
            learner_id: uptime.alive_ticks for learner_id, uptime in learner_uptime.items()
        },
        learner_failed_ticks={
            learner_id: uptime.failed_ticks for learner_id, uptime in learner_uptime.items()
        },
        learner_paused_ticks={
            learner_id: uptime.paused_ticks for learner_id, uptime in learner_uptime.items()
        },
        goodput_ratio=useful_tokens / total_tokens if total_tokens else 0.0,
        accepted_updates=committed * config.learners,
        final_loss=final_loss,
        learner_uptime=learner_uptime,
    )
    return BaselineResult(
        final_global_vector=global_vector,
        final_global_version=global_version,
        final_loss=final_loss,
        metrics=metrics,
    )


def run_decoupled_baseline(
    config: SimulationConfig,
    *,
    chaos_plan: ChaosPlan | None = None,
) -> SimulationResult:
    """Run the existing decoupled simulator as a baseline comparator."""

    return run_simulation(config, chaos_plan=chaos_plan)
