import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from decodilo.errors import ReplayMismatchError
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.syncer.event_log import EventLog
from decodilo.syncer.fragment_store import FragmentStore
from decodilo.syncer.global_state_store import write_global_vector_artifact
from decodilo.syncer.quorum import QuorumPolicy
from decodilo.syncer.replay import replay_event_log
from decodilo.trainer.fragment_artifacts import write_fragment_artifact
from decodilo.trainer.state_codec import make_fragment


def _run_local(
    workdir: Path,
    *,
    chunked: bool,
    restart: bool = False,
    steps: int = 40,
    run_id: str | None = None,
    artifact_transfer_mode: str = "bundle",
) -> dict:
    args = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "local",
        "run",
        "--learners",
        "2",
        "--steps",
        str(steps),
        "--min-quorum",
        "1",
        "--seed",
        "123",
        "--workdir",
        str(workdir),
        "--report-json",
        str(workdir / "report.json"),
        "--vector-dim",
        "4",
        "--fragments",
        "1",
        "--local-steps-per-sync",
        "10",
    ]
    if run_id is not None:
        args.extend(["--run-id", run_id])
    if chunked:
        args.extend(
            [
                "--payload-storage-mode",
                "chunked",
                "--global-update-storage-mode",
                "chunked",
                "--checkpoint-storage-mode",
                "chunked",
                "--merge-mode",
                "streaming_chunked",
                "--chunk-size-mb",
                "1",
                "--memory-budget-mb",
                "1",
                "--allow-spill-to-disk",
                "--artifact-transfer-mode",
                artifact_transfer_mode,
            ]
        )
    if restart:
        args.extend(
            [
                "--syncer-checkpoint-interval-rounds",
                "1",
                "--restart-syncer-after-round",
                "2",
            ]
        )
    subprocess.run(args, check=True, capture_output=True, text=True, timeout=30)
    return json.loads((workdir / "report.json").read_text(encoding="utf-8"))


def _events(workdir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (workdir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_chunked_syncer_control_commit_payloads_do_not_inline_vectors(tmp_path) -> None:
    service = SyncerService(
        SyncerServiceConfig(
            run_id="compact-control",
            workdir=tmp_path,
            vector_dim=13_216,
            learners=2,
            min_quorum=2,
            payload_storage_mode="chunked",
            global_update_storage_mode="chunked",
            checkpoint_storage_mode="chunked",
            merge_mode="streaming_chunked",
            inline_payload_max_bytes=1024,
            tensor_artifact_codec="binary_v1",
            fragment_artifact_codec="binary_v1",
            checkpoint_artifact_codec="binary_v1",
        )
    )
    first = np.ones(13_216, dtype=np.float64)
    second = np.full(13_216, 2.0, dtype=np.float64)
    service.store.submit_learner_update(
        learner_id="learner-0",
        vector=first,
        global_version_seen=0,
        tokens=64,
        submitted_at=1,
    )
    service.store.submit_learner_update(
        learner_id="learner-1",
        vector=second,
        global_version_seen=0,
        tokens=64,
        submitted_at=2,
    )

    commit = service._maybe_commit()

    assert commit is not None
    assert service.last_commit_payload is not None
    assert service.last_commit_payload["control_payload_compacted"] is True
    assert service.last_commit_payload["accepted_learner_ids"] == ["learner-0", "learner-1"]
    assert "old_global_vector" not in service.last_commit_payload
    assert "weighted_delta" not in service.last_commit_payload
    assert "new_global_vector" not in service.last_commit_payload
    serialized_payload = json.dumps(service.last_commit_payload)
    assert "global_vector" not in serialized_payload
    assert "weighted_delta" not in serialized_payload
    assert len(serialized_payload.encode("utf-8")) < 2048



@pytest.mark.integration
def test_live_chunked_runtime_supports_syncer_object_store_transfer(tmp_path) -> None:
    report = _run_local(tmp_path, chunked=True, artifact_transfer_mode="object_store")
    metrics = report["metrics"]

    assert report["artifact_transfer_mode"] == "object_store"
    assert report["artifact_storage_backend"] == "syncer_object_store"
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert metrics["chunked_fragment_submissions"] > 0

@pytest.mark.integration
def test_live_chunked_fragment_submission_update_delivery_and_replay(tmp_path) -> None:
    report = _run_local(tmp_path, chunked=True)
    events = _events(tmp_path)
    event_text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    metrics = report["metrics"]

    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert metrics["chunked_fragment_submissions"] > 0
    assert metrics["inline_fragment_submissions"] == 0
    assert metrics["artifact_ref_validations"] == metrics["chunked_fragment_submissions"]
    assert metrics["chunked_fragment_bytes_accepted"] > 0
    assert metrics["live_streaming_merges"] == metrics["committed_sync_rounds"]
    assert metrics["global_update_messages_sent"] >= metrics["global_update_acks"]
    assert metrics["global_update_acks"] > 0
    assert "global_vector_artifact_ref" in event_text
    assert '"vector": [' not in event_text
    assert '"global_vector": [' not in event_text
    assert '"data": [' not in event_text

    submitted = [event for event in events if event["event_type"] == "learner_fragment_submitted"]
    assert submitted
    assert all(event["payload"]["storage_kind"] == "artifact_ref" for event in submitted)
    assert all("artifact_ref" in event["payload"] for event in submitted)

    replayed = replay_event_log(tmp_path / "events.jsonl")
    assert replayed.replay_mode == "numeric_recompute"
    assert replayed.sync_rounds_committed == report["final_global_version"]


def test_inline_and_chunked_merge_paths_are_numerically_equivalent(tmp_path) -> None:
    initial = np.asarray([0.0, 0.0, 0.0, 0.0])
    learners = {
        "learner-0": (np.asarray([1.0, 2.0, 3.0, 4.0]), 10),
        "learner-1": (np.asarray([2.0, 4.0, 6.0, 8.0]), 30),
    }
    policy = QuorumPolicy(min_quorum=2, grace_window_ticks=0, max_staleness_versions=1)
    inline = FragmentStore(
        initial_global_vector=initial,
        num_fragments=1,
        quorum_policy=policy,
        event_log=EventLog(tmp_path / "inline.jsonl", run_id="run-equivalence", truncate=True),
    )
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )

    def write_vector_ref(role: str, vector: np.ndarray, version: int) -> dict:
        return write_global_vector_artifact(
            vector=vector,
            run_id="run-equivalence",
            global_version=version,
            artifact_id=f"run-equivalence:{role}:{version}",
            artifact_type="global_vector",
            transport=transport,
            manifest_path=tmp_path / "artifacts" / f"{role}-{version}.artifact.json",
            chunk_root=tmp_path / "chunks",
            chunk_size_bytes=128,
        ).model_dump(mode="json")

    chunked = FragmentStore(
        initial_global_vector=initial,
        num_fragments=1,
        quorum_policy=policy,
        event_log=EventLog(tmp_path / "chunked.jsonl", run_id="run-equivalence", truncate=True),
        event_payload_mode="chunked",
        merge_mode="streaming_chunked",
        global_vector_artifact_writer=write_vector_ref,
    )
    for index, (learner_id, (vector, tokens)) in enumerate(learners.items()):
        inline.submit_learner_update(
            learner_id=learner_id,
            vector=vector,
            global_version_seen=0,
            tokens=tokens,
            submitted_at=index,
        )
        fragment = make_fragment(
            trainer_type="numpy_convex",
            run_id="run-equivalence",
            learner_id=learner_id,
            fragment_id=0,
            global_version=0,
            data=vector,
            tokens=tokens,
        )
        ref = write_fragment_artifact(
            fragment=fragment,
            transport=transport,
            manifest_path=tmp_path / "artifacts" / f"{learner_id}.artifact.json",
            chunk_root=tmp_path / "chunks",
            chunk_size_bytes=128,
            created_by=learner_id,
        )
        chunked.submit_learner_update(
            learner_id=learner_id,
            vector=vector,
            global_version_seen=0,
            tokens=tokens,
            submitted_at=index,
            artifact_ref=ref.model_dump(mode="json"),
            payload_metadata={
                "checksum": fragment.checksum,
                "dtype": fragment.dtype,
                "shape": fragment.shape,
            },
        )

    inline.maybe_commit(current_tick=10)
    chunked.maybe_commit(current_tick=10)

    np.testing.assert_allclose(chunked.global_vector, inline.global_vector, rtol=0.0, atol=1e-12)
    assert chunked.metrics.live_streaming_merges == 1
    assert '"vector": [' not in (tmp_path / "chunked.jsonl").read_text(encoding="utf-8")


@pytest.mark.integration
def test_chunked_replay_rejects_missing_or_corrupt_artifact(tmp_path) -> None:
    _run_local(tmp_path, chunked=True)
    first_submission = next(
        event for event in _events(tmp_path) if event["event_type"] == "learner_fragment_submitted"
    )
    manifest_path = tmp_path / first_submission["payload"]["artifact_ref"]["manifest_path"]
    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(original.replace('"total_bytes"', '"tampered_total_bytes"', 1))

    with pytest.raises(ReplayMismatchError, match="artifact"):
        replay_event_log(tmp_path / "events.jsonl")
