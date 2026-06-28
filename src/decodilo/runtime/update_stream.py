"""Explicit global-update delivery and acknowledgement tracking."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from statistics import mean
from typing import Any


@dataclass
class UpdateStreamMetrics:
    global_update_broadcasts: int = 0
    global_update_messages_sent: int = 0
    global_update_acks: int = 0
    duplicate_global_update_acks: int = 0
    learner_update_lag_max: int = 0
    learner_update_lag_avg: float = 0.0
    stale_due_to_lag_count: int = 0


@dataclass
class UpdateStream:
    """Tracks learner global-version acknowledgements."""

    max_version_lag: int = 2
    learner_versions: dict[str, int] = field(default_factory=dict)
    metrics: UpdateStreamMetrics = field(default_factory=UpdateStreamMetrics)
    sent_versions: dict[str, set[int]] = field(default_factory=dict)
    acked_versions: dict[str, set[int]] = field(default_factory=dict)
    learner_update_lag_current: dict[str, int] = field(default_factory=dict)
    current_global_version: int = 0
    _update_event: asyncio.Event = field(default_factory=asyncio.Event)

    def register(self, learner_id: str, *, version: int) -> None:
        previous = self.learner_versions.get(learner_id, -1)
        self.learner_versions[learner_id] = max(previous, version)
        self.current_global_version = max(self.current_global_version, version)
        self.sent_versions.setdefault(learner_id, set())
        self.acked_versions.setdefault(learner_id, set())
        self.refresh_lag_metrics(current_version=version)

    def notify_commit(self, *, global_version: int) -> None:
        self.current_global_version = max(self.current_global_version, global_version)
        self.metrics.global_update_broadcasts += 1
        self._update_event.set()
        self.refresh_lag_metrics(current_version=global_version)

    async def wait_for_update(
        self,
        *,
        learner_id: str,
        learner_version: int,
        current_version: int,
        timeout_seconds: float,
    ) -> bool:
        effective_current_version = max(current_version, self.current_global_version)
        if learner_version < effective_current_version:
            return True
        try:
            await asyncio.wait_for(self._update_event.wait(), timeout=timeout_seconds)
        except (asyncio.TimeoutError, TimeoutError):
            return False
        finally:
            self._update_event.clear()
        effective_current_version = max(current_version, self.current_global_version)
        return learner_version < effective_current_version

    def mark_sent(self, learner_id: str, *, global_version: int) -> None:
        self.sent_versions.setdefault(learner_id, set()).add(global_version)
        self.metrics.global_update_messages_sent += 1

    def ack(self, learner_id: str, *, global_version: int, current_version: int) -> None:
        if global_version > current_version:
            raise ValueError("cannot acknowledge a future global_version")
        previous = self.learner_versions.get(learner_id, -1)
        sent = self.sent_versions.setdefault(learner_id, set())
        acked = self.acked_versions.setdefault(learner_id, set())
        if global_version in acked or global_version not in sent:
            self.metrics.duplicate_global_update_acks += 1
            self.refresh_lag_metrics(current_version=current_version)
            return
        acked.add(global_version)
        self.learner_versions[learner_id] = max(previous, global_version)
        self.metrics.global_update_acks += 1
        self.refresh_lag_metrics(current_version=current_version)

    def refresh_lag_metrics(self, *, current_version: int) -> None:
        if not self.learner_versions:
            self.learner_update_lag_current = {}
            self.metrics.learner_update_lag_max = 0
            self.metrics.learner_update_lag_avg = 0.0
            return
        self.learner_update_lag_current = {
            learner_id: max(current_version - version, 0)
            for learner_id, version in self.learner_versions.items()
        }
        lags = list(self.learner_update_lag_current.values())
        self.metrics.learner_update_lag_max = max(self.metrics.learner_update_lag_max, max(lags))
        self.metrics.learner_update_lag_avg = float(mean(lags))

    def stale_learners(self, *, current_version: int) -> set[str]:
        stale = {
            learner_id
            for learner_id, version in self.learner_versions.items()
            if current_version - version > self.max_version_lag
        }
        if stale:
            self.metrics.stale_due_to_lag_count += len(stale)
        return stale

    def metrics_dict(self) -> dict[str, Any]:
        missing = max(
            self.metrics.global_update_messages_sent - self.metrics.global_update_acks,
            0,
        )
        return {
            "global_update_broadcasts": self.metrics.global_update_broadcasts,
            "global_update_messages_sent": self.metrics.global_update_messages_sent,
            "global_update_acks": self.metrics.global_update_acks,
            "duplicate_global_update_acks": self.metrics.duplicate_global_update_acks,
            "missing_global_update_acks": missing,
            "learner_update_lag_current": dict(sorted(self.learner_update_lag_current.items())),
            "learner_update_lag_max": self.metrics.learner_update_lag_max,
            "learner_update_lag_avg": self.metrics.learner_update_lag_avg,
            "stale_due_to_lag_count": self.metrics.stale_due_to_lag_count,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_version_lag": self.max_version_lag,
            "current_global_version": self.current_global_version,
            "learner_versions": dict(self.learner_versions),
            "sent_versions": {
                learner_id: sorted(versions)
                for learner_id, versions in self.sent_versions.items()
            },
            "acked_versions": {
                learner_id: sorted(versions)
                for learner_id, versions in self.acked_versions.items()
            },
            "metrics": self.metrics_dict(),
        }

    def restore(self, payload: dict[str, Any]) -> None:
        self.max_version_lag = int(payload.get("max_version_lag", self.max_version_lag))
        self.learner_versions = {
            str(key): int(value)
            for key, value in dict(payload.get("learner_versions", {})).items()
        }
        self.current_global_version = int(
            payload.get(
                "current_global_version",
                max(self.learner_versions.values(), default=0),
            )
        )
        self.sent_versions = {
            str(key): {int(version) for version in versions}
            for key, versions in dict(payload.get("sent_versions", {})).items()
        }
        self.acked_versions = {
            str(key): {int(version) for version in versions}
            for key, versions in dict(payload.get("acked_versions", {})).items()
        }
        metrics = dict(payload.get("metrics", {}))
        self.metrics.global_update_broadcasts = int(metrics.get("global_update_broadcasts", 0))
        self.metrics.global_update_messages_sent = int(
            metrics.get("global_update_messages_sent", metrics.get("global_updates_sent", 0))
        )
        self.metrics.global_update_acks = int(metrics.get("global_update_acks", 0))
        self.metrics.duplicate_global_update_acks = int(
            metrics.get("duplicate_global_update_acks", 0)
        )
        self.metrics.learner_update_lag_max = int(
            metrics.get("learner_update_lag_max", metrics.get("max_learner_version_lag", 0))
        )
        self.metrics.learner_update_lag_avg = float(
            metrics.get(
                "learner_update_lag_avg",
                metrics.get("average_learner_version_lag", 0.0),
            )
        )
        self.metrics.stale_due_to_lag_count = int(metrics.get("stale_due_to_lag_count", 0))
        current_version = max(self.learner_versions.values(), default=0)
        self.refresh_lag_metrics(current_version=current_version)
