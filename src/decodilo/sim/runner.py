"""Deterministic CPU-only Decoupled DiLoCo simulation runner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from decodilo import __version__
from decodilo.learner.fake_learner import FakeLearner
from decodilo.learner.learner_state import LearnerState
from decodilo.pricing.budget import hourly_cost_for_cluster
from decodilo.pricing.models import PriceProfile
from decodilo.protocol.messages import LearnerStatus
from decodilo.sim.chaos import ChaosPlan
from decodilo.sim.fake_model import convex_loss, make_initial_vector, make_target_vector
from decodilo.sim.metrics import LearnerUptime, SimulationMetrics
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.fragment_store import FragmentStore
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.quorum import QuorumPolicy


@dataclass(frozen=True)
class SimulationConfig:
    learners: int = 4
    vector_dim: int = 8
    num_fragments: int = 2
    steps: int = 200
    local_steps_per_sync: int = 10
    min_quorum: int = 2
    grace_window_ticks: int = 0
    max_staleness_versions: int = 1
    allow_partial_round: bool = False
    seed: int = 123
    learner_lr: float = 0.05
    outer_lr: float = 1.0
    run_id: str | None = None

    def __post_init__(self) -> None:
        if self.learners <= 0:
            raise ValueError("learners must be positive")
        if self.vector_dim <= 0:
            raise ValueError("vector_dim must be positive")
        if self.num_fragments <= 0:
            raise ValueError("num_fragments must be positive")
        if self.steps <= 0:
            raise ValueError("steps must be positive")
        if self.local_steps_per_sync <= 0:
            raise ValueError("local_steps_per_sync must be positive")


def deterministic_run_id(config: SimulationConfig) -> str:
    """Derive a stable run id from config when the user did not supply one."""

    data = asdict(config)
    data["run_id"] = None
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return "run-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class SimulationResult:
    final_global_vector: NDArray[np.float64]
    final_global_version: int
    final_loss: float
    metrics: SimulationMetrics
    event_log_path: Path | None
    run_id: str
    config: SimulationConfig
    pricing_assumptions: PriceProfile | None = None

    def _metrics_dict(self) -> dict[str, Any]:
        return {
            "total_tokens_processed": self.metrics.total_tokens_processed,
            "useful_tokens_accepted": self.metrics.useful_tokens_accepted,
            "rejected_tokens": self.metrics.rejected_tokens,
            "stale_tokens": self.metrics.stale_tokens,
            "wasted_tokens": self.metrics.wasted_tokens,
            "committed_sync_rounds": self.metrics.committed_sync_rounds,
            "sync_rounds_committed": self.metrics.sync_rounds_committed,
            "skipped_sync_rounds": self.metrics.skipped_sync_rounds,
            "rejected_fragments": self.metrics.rejected_fragments,
            "stale_fragments": self.metrics.stale_fragments,
            "learner_uptime_ticks": self.metrics.learner_uptime_ticks,
            "learner_failed_ticks": self.metrics.learner_failed_ticks,
            "learner_paused_ticks": self.metrics.learner_paused_ticks,
            "goodput_ratio": self.metrics.goodput_ratio,
            "estimated_cost": self.metrics.estimated_cost,
            "cost_per_total_token": self.metrics.cost_per_total_token,
            "cost_per_useful_token": self.metrics.cost_per_useful_token,
            "accepted_updates": self.metrics.accepted_updates,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "final_global_version": self.final_global_version,
            "final_global_vector": self.final_global_vector.tolist(),
            "final_loss": self.final_loss,
            **self._metrics_dict(),
            "learner_uptime": {
                learner_id: {
                    "alive_ticks": uptime.alive_ticks,
                    "paused_ticks": uptime.paused_ticks,
                    "failed_ticks": uptime.failed_ticks,
                }
                for learner_id, uptime in self.metrics.learner_uptime.items()
            },
            "event_log_path": str(self.event_log_path) if self.event_log_path else None,
        }

    def to_report(self) -> dict[str, object]:
        return {
            "config": asdict(self.config),
            "metrics": self._metrics_dict(),
            "final_global_version": self.final_global_version,
            "final_loss": self.final_loss,
            "pricing_assumptions": (
                self.pricing_assumptions.model_dump(mode="json")
                if self.pricing_assumptions is not None
                else None
            ),
            "run_id": self.run_id,
            "code_version": __version__ or None,
        }

    def write_report_json(self, path: str | Path) -> None:
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(self.to_report(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class SimulationRunner:
    """Runs deterministic logical-time learner and syncer interactions."""

    def __init__(
        self,
        config: SimulationConfig,
        *,
        chaos_plan: ChaosPlan | None = None,
        event_log_path: str | Path | None = None,
        price_profile: PriceProfile | None = None,
    ) -> None:
        self.config = config
        self.run_id = config.run_id or deterministic_run_id(config)
        self.chaos_plan = chaos_plan or ChaosPlan()
        self.event_log = EventLog(event_log_path, run_id=self.run_id)
        self.event_log_path = Path(event_log_path) if event_log_path is not None else None
        self.price_profile = price_profile

    def _make_learners(self, initial_vector: NDArray[np.float64]) -> dict[str, FakeLearner]:
        learners: dict[str, FakeLearner] = {}
        for index in range(self.config.learners):
            learner_id = f"learner-{index}"
            throughput = 100 + index * 10
            state = LearnerState(
                learner_id=learner_id,
                local_step=0,
                tokens_processed=0,
                parameters=initial_vector.copy(),
                last_global_version_seen=0,
                status=LearnerStatus.ALIVE,
                throughput_tokens_per_step=throughput,
            )
            learners[learner_id] = FakeLearner(state, learning_rate=self.config.learner_lr)
        return learners

    def run(self) -> SimulationResult:
        initial_global = make_initial_vector(self.config.vector_dim)
        target = make_target_vector(self.config.vector_dim, seed=self.config.seed + 1)
        learners = self._make_learners(initial_global)

        store = FragmentStore(
            initial_global_vector=initial_global,
            num_fragments=self.config.num_fragments,
            quorum_policy=QuorumPolicy(
                min_quorum=self.config.min_quorum,
                grace_window_ticks=self.config.grace_window_ticks,
                max_staleness_versions=self.config.max_staleness_versions,
                allow_partial_round=self.config.allow_partial_round,
            ),
            optimizer=SGDOuterOptimizer(outer_lr=self.config.outer_lr),
            event_log=self.event_log,
        )

        for learner_id in sorted(learners):
            self.event_log.append(
                EventType.LEARNER_STARTED,
                logical_time=0,
                learner_id=learner_id,
                payload={"learner_id": learner_id},
            )

        final_tick = self.config.steps - 1
        for tick in range(self.config.steps):
            final_tick = tick
            self.chaos_plan.apply(
                tick=tick,
                learners=learners,
                event_log=self.event_log,
                current_global_version=store.global_version,
            )
            for learner_id in sorted(learners):
                learner = learners[learner_id]
                learner.tick(target_vector=target)
                if (
                    learner.state.status == LearnerStatus.ALIVE
                    and learner.state.local_step > 0
                    and learner.state.local_step % self.config.local_steps_per_sync == 0
                    and learner.state.tokens_since_last_sync > 0
                ):
                    update = learner.make_update()
                    store.submit_learner_update(
                        learner_id=update.learner_id,
                        vector=update.vector,
                        global_version_seen=update.global_version_seen,
                        tokens=update.tokens,
                        submitted_at=tick,
                    )

            self._maybe_commit_and_broadcast(store, learners, tick)

        for tick in range(
            self.config.steps,
            self.config.steps + self.config.grace_window_ticks + 2,
        ):
            final_tick = tick
            self._maybe_commit_and_broadcast(store, learners, tick)

        store.write_checkpoint(checkpoint_id="final", logical_time=final_tick + 1)
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
        learner_uptime_ticks = {
            learner_id: uptime.alive_ticks for learner_id, uptime in learner_uptime.items()
        }
        learner_failed_ticks = {
            learner_id: uptime.failed_ticks for learner_id, uptime in learner_uptime.items()
        }
        learner_paused_ticks = {
            learner_id: uptime.paused_ticks for learner_id, uptime in learner_uptime.items()
        }
        estimated_cost = None
        cost_per_total_token = None
        cost_per_useful_token = None
        if self.price_profile is not None:
            logical_hours = self.config.steps / 3600.0
            hourly_cost = hourly_cost_for_cluster(self.config.learners, self.price_profile)
            estimated_cost = hourly_cost * logical_hours
            if total_tokens > 0:
                cost_per_total_token = estimated_cost / total_tokens
            if store.metrics.useful_tokens > 0:
                cost_per_useful_token = estimated_cost / store.metrics.useful_tokens

        useful_tokens = store.metrics.useful_tokens
        final_loss = convex_loss(store.global_vector, target)
        metrics = SimulationMetrics(
            total_tokens_processed=total_tokens,
            useful_tokens_accepted=useful_tokens,
            rejected_tokens=store.metrics.rejected_tokens,
            stale_tokens=store.metrics.stale_tokens,
            wasted_tokens=total_tokens - useful_tokens,
            committed_sync_rounds=store.metrics.sync_rounds_committed,
            skipped_sync_rounds=store.metrics.sync_rounds_skipped,
            rejected_fragments=store.metrics.rejected_fragments,
            stale_fragments=store.metrics.stale_fragments,
            learner_uptime_ticks=learner_uptime_ticks,
            learner_failed_ticks=learner_failed_ticks,
            learner_paused_ticks=learner_paused_ticks,
            goodput_ratio=useful_tokens / total_tokens if total_tokens else 0.0,
            estimated_cost=estimated_cost,
            cost_per_total_token=cost_per_total_token,
            cost_per_useful_token=cost_per_useful_token,
            accepted_updates=store.metrics.accepted_updates,
            final_loss=final_loss,
            learner_uptime=learner_uptime,
        )
        return SimulationResult(
            final_global_vector=store.global_vector.copy(),
            final_global_version=store.global_version,
            final_loss=metrics.final_loss,
            metrics=metrics,
            event_log_path=self.event_log_path,
            run_id=self.run_id,
            config=self.config,
            pricing_assumptions=self.price_profile,
        )

    def _maybe_commit_and_broadcast(
        self,
        store: FragmentStore,
        learners: dict[str, FakeLearner],
        tick: int,
    ) -> None:
        failed_ids = {
            learner_id
            for learner_id, learner in learners.items()
            if learner.state.status == LearnerStatus.FAILED
        }
        commit = store.maybe_commit(current_tick=tick, failed_learner_ids=failed_ids)
        if commit is None:
            return
        accepted_ids = set(commit.accepted_learner_ids)
        for learner_id, learner in learners.items():
            if learner_id in accepted_ids:
                learner.mark_update_accepted()
            if learner.state.status != LearnerStatus.FAILED:
                learner.receive_global(
                    store.global_vector,
                    global_version=store.global_version,
                )


def run_simulation(
    config: SimulationConfig,
    *,
    chaos_plan: ChaosPlan | None = None,
    event_log_path: str | Path | None = None,
    price_profile: PriceProfile | None = None,
) -> SimulationResult:
    runner = SimulationRunner(
        config,
        chaos_plan=chaos_plan,
        event_log_path=event_log_path,
        price_profile=price_profile,
    )
    return runner.run()

