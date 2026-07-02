"""Replay deterministic event logs into compact verification state."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from decodilo.errors import ReplayMismatchError
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.syncer.event_log import EventType, LogEvent, make_event_id, read_event_log
from decodilo.syncer.global_state_store import read_global_vector_artifact
from decodilo.syncer.outer_optimizer import create_outer_optimizer
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge
from decodilo.trainer.fragment_artifacts import read_fragment_artifact


@dataclass(frozen=True)
class ReplaySubmission:
    """Latest submitted update for one learner."""

    learner_id: str
    vector: NDArray[np.float64]
    tokens: int
    global_version_seen: int
    event_id: str
    artifact_ref: dict | None = None


@dataclass
class ReplayState:
    """State reconstructed from committed and rejected events."""

    global_versions: list[int] = field(default_factory=list)
    final_global_vector: NDArray[np.float64] | None = None
    accepted_useful_tokens: int = 0
    rejected_update_count: int = 0
    rejected_tokens: int = 0
    stale_tokens: int = 0
    skipped_sync_rounds: int = 0
    sync_round_composition: list[list[str]] = field(default_factory=list)
    replay_mode: str = "numeric_recompute"

    @property
    def sync_rounds_committed(self) -> int:
        return len(self.global_versions)


def _require_payload_fields(event: LogEvent, fields: set[str]) -> None:
    missing = sorted(field for field in fields if field not in event.payload)
    if missing:
        raise ReplayMismatchError(f"{event.event_id} missing payload fields: {missing}")


def _assert_vectors_close(
    actual: NDArray[np.float64],
    expected: NDArray[np.float64],
    *,
    label: str,
) -> None:
    if actual.shape != expected.shape or not np.allclose(actual, expected, rtol=0.0, atol=1e-12):
        raise ReplayMismatchError(f"{label} does not match replay-computed vector")


def _transport_for_artifacts(
    artifact_workdir: Path | None,
    artifact_transport: LocalArtifactTransport | None = None,
) -> LocalArtifactTransport:
    if artifact_transport is not None:
        return artifact_transport
    if artifact_workdir is None:
        raise ReplayMismatchError("chunked replay requires artifact_workdir")
    return LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(artifact_workdir),
            artifact_root=str(artifact_workdir / "artifacts"),
        )
    )


def _read_vector_ref(
    ref: dict,
    *,
    artifact_workdir: Path | None,
    artifact_transport: LocalArtifactTransport | None = None,
    expected_version: int | None = None,
) -> NDArray[np.float64]:
    try:
        vector, version = read_global_vector_artifact(
            ref=ref,
            transport=_transport_for_artifacts(artifact_workdir, artifact_transport),
        )
    except Exception as exc:  # noqa: BLE001 - replay failures should be explicit
        raise ReplayMismatchError(f"failed to read chunked global vector artifact: {exc}") from exc
    if expected_version is not None and version != expected_version:
        raise ReplayMismatchError("chunked global vector artifact version mismatch")
    return np.asarray(vector, dtype=np.float64)


def _read_submission_from_artifact(
    ref: dict,
    *,
    artifact_workdir: Path | None,
    artifact_transport: LocalArtifactTransport | None = None,
) -> tuple[NDArray[np.float64], int, int]:
    try:
        fragment = read_fragment_artifact(
            ref=ref,
            transport=_transport_for_artifacts(artifact_workdir, artifact_transport),
        )
    except Exception as exc:  # noqa: BLE001 - replay failures should be explicit
        raise ReplayMismatchError(
            f"failed to read chunked trainer fragment artifact: {exc}"
        ) from exc
    return (
        np.asarray(fragment.data, dtype=np.float64),
        int(fragment.tokens),
        int(fragment.global_version),
    )


def replay_events(
    events: Iterable[LogEvent],
    *,
    allow_out_of_order: bool = False,
    artifact_workdir: Path | None = None,
    artifact_transport: LocalArtifactTransport | None = None,
    initial_global_version: int = 0,
    initial_global_vector: NDArray[np.float64] | None = None,
    initial_useful_tokens: int = 0,
) -> ReplayState:
    """Replay events and validate sync-round sequence, tokens, and vectors."""

    state = ReplayState()
    if initial_global_version > 0:
        state.global_versions.append(initial_global_version)
    state.accepted_useful_tokens = initial_useful_tokens
    if initial_global_vector is not None:
        state.final_global_vector = np.asarray(initial_global_vector, dtype=np.float64).copy()
    pending: dict[str, ReplaySubmission] = {}
    started_rounds: dict[str, dict[str, object]] = {}
    current_global_vector: NDArray[np.float64] | None = (
        np.asarray(initial_global_vector, dtype=np.float64).copy()
        if initial_global_vector is not None
        else None
    )
    current_version = initial_global_version
    previous_logical_time = -1
    run_id: str | None = None
    replay_outer_optimizer = None
    replay_outer_optimizer_name: str | None = None

    for event in events:
        if event.event_id != make_event_id(event.run_id, event.sequence, event.event_type):
            raise ReplayMismatchError(f"{event.event_id} is not the deterministic event id")
        if run_id is None:
            run_id = event.run_id
        elif event.run_id != run_id:
            raise ReplayMismatchError("event log contains multiple run_id values")
        if not allow_out_of_order and event.logical_time < previous_logical_time:
            raise ReplayMismatchError("event logical_time is out of order")
        previous_logical_time = event.logical_time

        if event.event_type == EventType.LEARNER_FRAGMENT_SUBMITTED:
            if "artifact_ref" in event.payload:
                _require_payload_fields(
                    event,
                    {"learner_id", "global_version_seen", "tokens", "artifact_ref"},
                )
                vector, artifact_tokens, artifact_version = _read_submission_from_artifact(
                    dict(event.payload["artifact_ref"]),
                    artifact_workdir=artifact_workdir,
                    artifact_transport=artifact_transport,
                )
                state.replay_mode = "numeric_recompute"
                if artifact_tokens != int(event.payload["tokens"]):
                    raise ReplayMismatchError("artifact token count does not match event")
                if artifact_version != int(event.payload["global_version_seen"]):
                    raise ReplayMismatchError("artifact global_version does not match event")
                artifact_ref = dict(event.payload["artifact_ref"])
            else:
                _require_payload_fields(
                    event,
                    {"learner_id", "global_version_seen", "tokens", "vector"},
                )
                vector = np.asarray(event.payload["vector"], dtype=np.float64)
                artifact_ref = None
            learner_id = str(event.learner_id or event.payload["learner_id"])
            tokens = int(event.payload["tokens"])
            if tokens < 0:
                raise ReplayMismatchError("submitted token count cannot be negative")
            pending[learner_id] = ReplaySubmission(
                learner_id=learner_id,
                vector=vector,
                tokens=tokens,
                global_version_seen=int(event.payload["global_version_seen"]),
                event_id=event.event_id,
                artifact_ref=artifact_ref,
            )
        elif event.event_type == EventType.FRAGMENT_REJECTED:
            _require_payload_fields(event, {"learner_id", "reason", "tokens"})
            learner_id = str(event.learner_id or event.payload["learner_id"])
            submission = pending.pop(learner_id, None)
            if submission is None:
                raise ReplayMismatchError(f"rejected learner {learner_id} had no submission")
            logged_tokens = int(event.payload["tokens"])
            if logged_tokens != submission.tokens:
                raise ReplayMismatchError("rejected token count does not match submission")
            state.rejected_update_count += 1
            state.rejected_tokens += logged_tokens
            if event.payload["reason"] == "stale":
                state.stale_tokens += logged_tokens
        elif event.event_type == EventType.SYNC_ROUND_STARTED:
            _require_payload_fields(
                event,
                {"round_id", "previous_global_version", "accepted_learner_ids"},
            )
            round_id = str(event.round_id or event.payload["round_id"])
            if round_id in started_rounds:
                raise ReplayMismatchError(f"round {round_id} started twice")
            previous_version = int(event.payload["previous_global_version"])
            if previous_version != current_version:
                raise ReplayMismatchError("sync round started from unexpected global_version")
            started_rounds[round_id] = event.payload
        elif event.event_type == EventType.SYNC_ROUND_COMMITTED:
            chunked_commit = "new_global_vector_artifact_ref" in event.payload
            required_fields = {
                "round_id",
                "previous_global_version",
                "new_global_version",
                "accepted_learner_ids",
                "useful_tokens",
                "outer_lr",
            }
            if chunked_commit:
                required_fields |= {
                    "old_global_vector_artifact_ref",
                    "weighted_delta_artifact_ref",
                    "new_global_vector_artifact_ref",
                    "numeric_merge_performed",
                    "simulation_only",
                }
            else:
                required_fields |= {
                    "old_global_vector",
                    "weighted_delta",
                    "new_global_vector",
                }
            _require_payload_fields(event, required_fields)
            payload = event.payload
            if chunked_commit and (
                not bool(payload["numeric_merge_performed"]) or bool(payload["simulation_only"])
            ):
                raise ReplayMismatchError(
                    "chunked numeric replay cannot accept metadata-only merge"
                )
            round_id = str(event.round_id or payload["round_id"])
            started = started_rounds.pop(round_id, None)
            if started is None:
                raise ReplayMismatchError(f"round {round_id} committed before start")

            previous_version = int(payload["previous_global_version"])
            new_version = int(payload["new_global_version"])
            if previous_version != current_version or new_version != current_version + 1:
                raise ReplayMismatchError("global_version sequence is invalid")

            accepted_ids = list(payload["accepted_learner_ids"])
            if accepted_ids != list(started["accepted_learner_ids"]):
                raise ReplayMismatchError("committed learners differ from sync start")
            submissions = []
            for learner_id in accepted_ids:
                submission = pending.get(str(learner_id))
                if submission is None:
                    raise ReplayMismatchError(
                        f"accepted learner {learner_id} had no submitted fragment"
                    )
                submissions.append(submission)

            if chunked_commit:
                old_vector = _read_vector_ref(
                    dict(payload["old_global_vector_artifact_ref"]),
                    artifact_workdir=artifact_workdir,
                    artifact_transport=artifact_transport,
                    expected_version=previous_version,
                )
                logged_delta = _read_vector_ref(
                    dict(payload["weighted_delta_artifact_ref"]),
                    artifact_workdir=artifact_workdir,
                    artifact_transport=artifact_transport,
                    expected_version=new_version,
                )
                logged_new_vector = _read_vector_ref(
                    dict(payload["new_global_vector_artifact_ref"]),
                    artifact_workdir=artifact_workdir,
                    artifact_transport=artifact_transport,
                    expected_version=new_version,
                )
            else:
                old_vector = np.asarray(payload["old_global_vector"], dtype=np.float64)
                logged_delta = np.asarray(payload["weighted_delta"], dtype=np.float64)
                logged_new_vector = np.asarray(payload["new_global_vector"], dtype=np.float64)
            if current_global_vector is None:
                current_global_vector = old_vector
            else:
                _assert_vectors_close(
                    old_vector,
                    current_global_vector,
                    label="old_global_vector",
                )

            useful_tokens = sum(submission.tokens for submission in submissions)
            if int(payload["useful_tokens"]) != useful_tokens:
                raise ReplayMismatchError("useful token count does not match accepted fragments")

            optimizer_name = str(payload.get("outer_optimizer", "sgd"))
            if replay_outer_optimizer is None or replay_outer_optimizer_name != optimizer_name:
                outer_momentum = payload.get("outer_momentum", 0.9)
                replay_outer_optimizer = create_outer_optimizer(
                    optimizer_name,
                    outer_lr=float(payload["outer_lr"]),
                    momentum=0.9 if outer_momentum is None else float(outer_momentum),
                )
                replay_outer_optimizer_name = optimizer_name
            merge = token_weighted_merge(
                current_global_vector,
                [
                    LearnerDelta(
                        learner_id=submission.learner_id,
                        vector=submission.vector,
                        tokens=submission.tokens,
                        global_version_seen=submission.global_version_seen,
                    )
                    for submission in submissions
                ],
                optimizer=replay_outer_optimizer,
            )
            _assert_vectors_close(
                logged_delta,
                merge.weighted_delta,
                label="weighted_delta",
            )
            _assert_vectors_close(
                logged_new_vector,
                merge.new_global_vector,
                label="new_global_vector",
            )

            current_global_vector = merge.new_global_vector.copy()
            current_version = new_version
            state.global_versions.append(new_version)
            state.final_global_vector = current_global_vector.copy()
            state.accepted_useful_tokens += useful_tokens
            state.sync_round_composition.append([str(learner_id) for learner_id in accepted_ids])
            for learner_id in accepted_ids:
                pending.pop(str(learner_id), None)
        elif event.event_type == EventType.SYNC_ROUND_SKIPPED:
            state.skipped_sync_rounds += 1
        elif event.event_type in {
            EventType.GLOBAL_UPDATE_SENT,
            EventType.GLOBAL_UPDATE_ACKED,
        }:
            _require_payload_fields(event, {"learner_id", "global_version"})
            if int(event.payload["global_version"]) > current_version:
                raise ReplayMismatchError(
                    "update delivery event references a future global_version"
                )
        elif event.event_type == EventType.SYNCER_CHECKPOINT_WRITTEN:
            _require_payload_fields(event, {"global_version", "checkpoint_path", "checksum"})
            if int(event.payload["global_version"]) != current_version:
                raise ReplayMismatchError("syncer checkpoint global_version does not match replay")
        elif event.event_type == EventType.SYNCER_RECOVERED:
            _require_payload_fields(event, {"global_version", "checkpoint_run_id"})
            if str(event.payload["checkpoint_run_id"]) != event.run_id:
                raise ReplayMismatchError("syncer recovery checkpoint run_id mismatch")
            recovered_version = int(event.payload["global_version"])
            if recovered_version < current_version:
                raise ReplayMismatchError("syncer recovery regressed global_version")
            current_version = recovered_version
        elif event.event_type == EventType.LEARNER_RECONNECTED:
            _require_payload_fields(event, {"learner_id", "recovery_version"})
            if int(event.payload["recovery_version"]) > current_version:
                raise ReplayMismatchError("learner reconnected to future global_version")
        elif event.event_type == EventType.CHECKPOINT_WRITTEN:
            if "global_vector_artifact_ref" in event.payload:
                _require_payload_fields(event, {"global_version", "global_vector_artifact_ref"})
            else:
                _require_payload_fields(event, {"global_version", "global_vector"})
            if int(event.payload["global_version"]) != current_version:
                raise ReplayMismatchError("checkpoint global_version does not match replay")
            if current_global_vector is not None:
                checkpoint_vector = (
                    _read_vector_ref(
                        dict(event.payload["global_vector_artifact_ref"]),
                        artifact_workdir=artifact_workdir,
                        artifact_transport=artifact_transport,
                        expected_version=current_version,
                    )
                    if "global_vector_artifact_ref" in event.payload
                    else np.asarray(event.payload["global_vector"], dtype=np.float64)
                )
                _assert_vectors_close(
                    checkpoint_vector,
                    current_global_vector,
                    label="checkpoint vector",
                )

    if started_rounds:
        raise ReplayMismatchError(f"uncommitted started rounds remain: {sorted(started_rounds)}")
    return state


def replay_event_log(
    path: str | Path,
    *,
    allow_out_of_order: bool = False,
    artifact_transport: LocalArtifactTransport | None = None,
) -> ReplayState:
    """Replay a JSONL event log from disk."""

    event_log_path = Path(path)
    return replay_events(
        read_event_log(event_log_path),
        allow_out_of_order=allow_out_of_order,
        artifact_workdir=event_log_path.parent,
        artifact_transport=artifact_transport,
    )
